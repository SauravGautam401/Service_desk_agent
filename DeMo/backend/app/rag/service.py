from app.rag.loader import load_knowledge_base
from app.rag.chunker import chunk_documents
from app.rag.embeddings import (
    create_embeddings,
    create_query_embedding
)
from app.rag.vector_store import VectorStore
from app.rag.llm import generate_answer


documents = load_knowledge_base(
    "knowledge_base"
)

chunks = chunk_documents(documents)

texts = [
    chunk["text"]
    for chunk in chunks
]

embeddings = create_embeddings(texts)

dimension = embeddings.shape[1]

vector_store = VectorStore(
    dimension
)

vector_store.add(
    embeddings,
    chunks
)



def ask_rag(question: str):

    query_embedding = create_query_embedding(
        question
    )

   
    results = vector_store.search(
        query_embedding,
        k=3
    )

   
    context = "\n\n".join(
        result["text"]
        for result in results
    )

   
    answer = generate_answer(
        question,
        context
    )

    return answer