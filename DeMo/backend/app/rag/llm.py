import threading

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    StoppingCriteria,
    StoppingCriteriaList,
    TextIteratorStreamer,
)

from app.rag.stopping import STOP_SEQUENCES, StopFilter, truncate_at_stop

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
model.eval()

# Qwen uses ChatML: <|im_end|> ends a turn, <|endoftext|> ends the document.
# Listing both makes generation stop at the end of the assistant turn.
EOS_IDS = sorted({
    i for i in (
        tokenizer.convert_tokens_to_ids("<|im_end|>"),
        tokenizer.convert_tokens_to_ids("<|endoftext|>"),
        tokenizer.eos_token_id,
    ) if isinstance(i, int) and i >= 0
})
PAD_ID = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else EOS_IDS[0]

GEN_KWARGS = dict(
    max_new_tokens=300,          # 100 was cutting answers mid-sentence
    do_sample=False,
    repetition_penalty=1.1,      # stops "the the the..." loops
    eos_token_id=EOS_IDS,
    pad_token_id=PAD_ID,
    stop_strings=STOP_SEQUENCES,  # HF name for stop_sequences (transformers >= 4.39)
)

SYSTEM_PROMPT = """You are the IT Service Desk assistant for an internal company help desk.
Answer using ONLY the Knowledge Base excerpts given in the user message.

Rules:
1. Use only facts from the Knowledge Base. Never invent steps, links, or contact details.
2. Give ONE short, practical answer (under 120 words). Use numbered steps for procedures and Markdown code blocks for commands.
3. If the Knowledge Base does not contain the answer, reply exactly: "I don't have enough information in the knowledge base."
4. Write only your own reply. Never write "User:", "Human:", or "Question:", never repeat the question, and never continue the conversation. Stop after the answer."""

# Only one generation at a time on a single local model.
_gen_lock = threading.Lock()


def _build_inputs(question, context):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Knowledge Base:\n{context}\n\nQuestion: {question}"},
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return tokenizer(prompt, return_tensors="pt")


def generate_answer(question, context):
    """Blocking generation; returns the cleaned answer string."""
    inputs = _build_inputs(question, context)
    with _gen_lock, torch.no_grad():
        outputs = model.generate(**inputs, tokenizer=tokenizer, **GEN_KWARGS)
    new_tokens = outputs[0][inputs.input_ids.shape[1]:]
    text = tokenizer.decode(new_tokens, skip_special_tokens=True)
    return truncate_at_stop(text)


class _Cancel(StoppingCriteria):
    """Lets us abort generation if the browser disconnects."""

    def __init__(self):
        self.cancelled = False

    def __call__(self, input_ids, scores, **kwargs):
        return torch.full((input_ids.shape[0],), self.cancelled, dtype=torch.bool, device=input_ids.device)


def stream_answer(question, context):
    """Yield the answer text piece by piece (stop sequences already removed)."""
    inputs = _build_inputs(question, context)
    streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
    cancel = _Cancel()

    def run():
        with torch.no_grad():
            model.generate(
                **inputs, tokenizer=tokenizer, streamer=streamer,
                stopping_criteria=StoppingCriteriaList([cancel]), **GEN_KWARGS,
            )

    with _gen_lock:
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        flt = StopFilter()
        try:
            for piece in streamer:
                out = flt.feed(piece)
                if out:
                    yield out
                if flt.stopped:
                    break
            tail = flt.flush()
            if tail:
                yield tail
        finally:
            cancel.cancelled = True   # no-op if already finished
            thread.join()
