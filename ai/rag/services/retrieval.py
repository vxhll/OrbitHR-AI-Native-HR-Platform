from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


VECTORSTORE_DIR = Path(__file__).resolve().parent.parent / "vectorstore"

COLLECTION_NAME = "orbithr_hr_policies"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class PolicyRetriever:
    def __init__(self):
        self.model = SentenceTransformer(EMBEDDING_MODEL)

        self.client = chromadb.PersistentClient(
            path=str(VECTORSTORE_DIR)
        )

        self.collection = self.client.get_collection(
            name=COLLECTION_NAME
        )

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        query_embedding = self.model.encode(
            [query],
            normalize_embeddings=True,
        ).tolist()

        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
        )

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        retrieved_chunks = []

        for document, metadata, distance in zip(
            documents,
            metadatas,
            distances,
        ):
            retrieved_chunks.append(
                {
                    "text": document,
                    "source": metadata["source"],
                    "chunk_index": metadata["chunk_index"],
                    "distance": round(float(distance), 4),
                }
            )

        return retrieved_chunks


if __name__ == "__main__":
    retriever = PolicyRetriever()

    query = input("\nEnter HR policy question: ").strip()

    results = retriever.search(query)

    print("\nOrbitHR Policy Retrieval")
    print("------------------------")
    print(f"Query: {query}")
    print(f"Results: {len(results)}")

    for index, result in enumerate(results, start=1):
        print(f"\nResult {index}")
        print(f"Source: {result['source']}")
        print(f"Distance: {result['distance']}")
        print(f"Text: {result['text'][:500]}")