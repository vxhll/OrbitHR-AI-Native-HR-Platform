from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from document_ingestion import build_chunks


VECTORSTORE_DIR = Path(__file__).resolve().parent.parent / "vectorstore"

COLLECTION_NAME = "orbithr_hr_policies"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def build_vector_store():
    print("\nOrbitHR RAG Vector Store")
    print("------------------------")

    chunks = build_chunks()

    print(f"Chunks received: {len(chunks)}")
    print(f"Embedding model: {EMBEDDING_MODEL}")

    model = SentenceTransformer(EMBEDDING_MODEL)

    client = chromadb.PersistentClient(
        path=str(VECTORSTORE_DIR)
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    documents = [chunk["text"] for chunk in chunks]

    ids = [chunk["chunk_id"] for chunk in chunks]

    metadatas = [
        {
            "source": chunk["source"],
            "chunk_index": chunk["chunk_index"],
        }
        for chunk in chunks
    ]

    embeddings = model.encode(
        documents,
        normalize_embeddings=True,
    ).tolist()

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    print(f"Documents stored: {collection.count()}")
    print(f"Vector store: {VECTORSTORE_DIR}")

    return collection


if __name__ == "__main__":
    build_vector_store()