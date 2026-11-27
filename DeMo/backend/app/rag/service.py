from pathlib import Path

from app.rag.loader import load_knowledge_base
from app.rag.chunker import chunk_documents
from app.rag.embeddings import create_embeddings, create_query_embedding
from app.rag.vector_store import VectorStore
from app.rag.llm import generate_answer, stream_answer

# Absolute path: works no matter which folder uvicorn is started from.
KB_DIR = Path(__file__).resolve().parents[2] / "knowledge_base"
NO_ANSWER_PREFIX = "I don't have enough information"

documents = load_knowledge_base(KB_DIR)
chunks = chunk_documents(documents)
embeddings = create_embeddings([c["text"] for c in chunks])

vector_store = VectorStore(embeddings.shape[1])
vector_store.add(embeddings, chunks)


def retrieve(question: str, k: int = 3):
    """Return (context, unique_source_filenames) for a question."""
    results = vector_store.search(create_query_embedding(question), k=k)
    context = "\n\n".join(r["text"] for r in results)
    sources = list(dict.fromkeys(r["source"] for r in results))
    return context, sources


def _visible_sources(answer: str, sources):
    # Don't cite files when the model said it found nothing.
    return [] if answer.strip().startswith(NO_ANSWER_PREFIX) else sources


def ask_rag(question: str) -> dict:
    context, sources = retrieve(question)
    answer = generate_answer(question, context)
    return {"response": answer, "sources": _visible_sources(answer, sources)}


def stream_rag(question: str):
    """Yield ('token', text) events, then one ('done', {'sources': [...]})."""
    context, sources = retrieve(question)
    parts = []
    for piece in stream_answer(question, context):
        parts.append(piece)
        yield "token", piece
    yield "done", {"sources": _visible_sources("".join(parts), sources)}
