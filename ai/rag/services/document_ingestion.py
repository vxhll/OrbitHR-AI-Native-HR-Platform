from pathlib import Path


DOCUMENTS_DIR = (
    Path(__file__).resolve().parent.parent / "documents"
)


def load_documents() -> list[dict]:
    documents = []

    for file_path in sorted(DOCUMENTS_DIR.glob("*.txt")):
        text = file_path.read_text(
            encoding="utf-8"
        ).strip()

        if not text:
            continue

        documents.append(
            {
                "source": file_path.name,
                "text": text,
            }
        )

    return documents


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> list[str]:

    words = text.split()

    chunks = []

    start = 0

    while start < len(words):

        end = start + chunk_size

        chunk = " ".join(
            words[start:end]
        )

        if chunk:
            chunks.append(chunk)

        if end >= len(words):
            break

        start = end - chunk_overlap

    return chunks


def build_chunks() -> list[dict]:

    documents = load_documents()

    chunks = []

    for document in documents:

        document_chunks = chunk_text(
            document["text"]
        )

        for index, chunk in enumerate(
            document_chunks
        ):

            chunks.append(
                {
                    "chunk_id": (
                        f"{document['source']}"
                        f":chunk_{index}"
                    ),
                    "source": document["source"],
                    "chunk_index": index,
                    "text": chunk,
                }
            )

    return chunks


if __name__ == "__main__":

    chunks = build_chunks()

    print("\nOrbitHR RAG Document Ingestion")
    print("-------------------------------")

    print(
        f"Documents loaded: "
        f"{len(load_documents())}"
    )

    print(
        f"Chunks created: "
        f"{len(chunks)}"
    )

    print("\nChunks:")

    for chunk in chunks:
        print(
            f"\n[{chunk['chunk_id']}]"
        )
        print(chunk["text"][:300])