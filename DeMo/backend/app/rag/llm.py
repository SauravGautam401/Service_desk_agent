from transformers import AutoTokenizer, AutoModelForCausalLM
import torch


MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME
)


def generate_answer(question, context):

    messages = [
        {
            "role": "system",
            "content": """
You are an IT Service Desk assistant.

Answer the user's question ONLY using the information
provided in the knowledge base.

Rules:
1. Do not use outside knowledge.
2. Do not make assumptions.
3. Do not add troubleshooting steps that are not in the context.
4. Keep the answer short and practical.
5. If the context does not contain the answer, respond exactly:
"I don't have enough information in the knowledge base."
"""
        },
        {
            "role": "user",
            "content": f"""
Knowledge Base:

{context}

Question:

{question}

Answer:
"""
        }
    ]

    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        clean_up_tokenization_spaces=False
    )

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=100,
            do_sample=False
        )

    generated_tokens = outputs[0][inputs.input_ids.shape[1]:]

    answer = tokenizer.decode(
        generated_tokens,
        skip_special_tokens=True
    )

    return answer.strip()