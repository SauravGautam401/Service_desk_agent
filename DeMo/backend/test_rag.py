from app.rag.loader import load_knowledge_base
from app.rag.chunker import chunk_documents
from app.rag.embeddings import (
    create_embeddings,
    create_query_embedding
)
from app.rag.vector_store import VectorStore
from app.rag.llm import generate_answer


# --------------------------------
# 1. LOAD KNOWLEDGE BASE
# --------------------------------

documents = load_knowledge_base(
    "knowledge_base"
)

print("Documents loaded:", len(documents))


# --------------------------------
# 2. CREATE CHUNKS
# --------------------------------

chunks = chunk_documents(documents)

print("Chunks created:", len(chunks))


# --------------------------------
# 3. EXTRACT TEXT
# --------------------------------

texts = [
    chunk["text"]
    for chunk in chunks
]


# --------------------------------
# 4. CREATE EMBEDDINGS
# --------------------------------

embeddings = create_embeddings(texts)

print(
    "Embedding shape:",
    embeddings.shape
)


# --------------------------------
# 5. CREATE VECTOR STORE
# --------------------------------

dimension = embeddings.shape[1]

vector_store = VectorStore(
    dimension
)


# --------------------------------
# 6. STORE DOCUMENTS
# --------------------------------

vector_store.add(
    embeddings,
    chunks
)


# --------------------------------
# 7. ASK QUESTION
# --------------------------------

question = input(
    "\nAsk your IT question: "
)


# --------------------------------
# 8. CREATE QUESTION EMBEDDING
# --------------------------------

query_embedding = create_query_embedding(
    question
)


# --------------------------------
# 9. RETRIEVE RELEVANT CHUNKS
# --------------------------------

results = vector_store.search(
    query_embedding,
    k=3
)


# --------------------------------
# 10. DISPLAY RETRIEVED CONTEXT
# --------------------------------

print(
    "\n========== RETRIEVED CONTEXT ==========\n"
)

for i, result in enumerate(
    results,
    start=1
):

    print(f"Result {i}")
    print(f"Source: {result['source']}")
    print(f"Distance: {result['distance']:.4f}")
    print()
    print(result["text"])
    print("\n" + "-" * 60)


# --------------------------------
# 11. BUILD CONTEXT FOR LLM
# --------------------------------

context = "\n\n".join(
    result["text"]
    for result in results
)


# --------------------------------
# 12. GENERATE ANSWER
# --------------------------------

answer = generate_answer(
    question,
    context
)


# --------------------------------
# 13. DISPLAY FINAL ANSWER
# --------------------------------

print(
    "\n========== FINAL ANSWER ==========\n"
)

print(answer)