from pathlib import Path

import pytest

from app.services.rag.chunker import PolicyChunker
from app.services.rag.document_loader import PolicyDocumentLoader


def test_document_loader_loads_policy_files(tmp_path: Path):
    (tmp_path / "leave_policy.txt").write_text(
        "Policy ID: HR-LEAVE-001\n\n"
        "1. PURPOSE\nThis policy explains leave.",
        encoding="utf-8",
    )
    (tmp_path / "empty_policy.txt").write_text("   ", encoding="utf-8")
    (tmp_path / "ignored.md").write_text("Not a policy text file", encoding="utf-8")

    documents = PolicyDocumentLoader(str(tmp_path)).load_documents()

    assert len(documents) == 1
    assert documents[0]["source"] == "leave_policy.txt"
    assert documents[0]["policy_id"] == "HR-LEAVE-001"
    assert "This policy explains leave." in documents[0]["text"]


def test_document_loader_rejects_missing_directory(tmp_path: Path):
    missing_directory = tmp_path / "missing"

    with pytest.raises(FileNotFoundError):
        PolicyDocumentLoader(str(missing_directory)).load_documents()


def test_chunker_preserves_policy_metadata():
    chunker = PolicyChunker()
    documents = [
        {
            "source": "leave_policy.txt",
            "policy_id": "HR-LEAVE-001",
            "text": (
                "Policy ID: HR-LEAVE-001\n\n"
                "1. PURPOSE\nThis policy explains leave.\n\n"
                "2. ENTITLEMENT\nEmployees receive annual leave."
            ),
        }
    ]

    chunks = chunker.chunk_documents(documents)

    assert len(chunks) >= 2
    assert all(chunk["metadata"]["source"] == "leave_policy.txt" for chunk in chunks)
    assert all(chunk["metadata"]["policy_id"] == "HR-LEAVE-001" for chunk in chunks)
    assert {chunk["metadata"]["section"] for chunk in chunks} >= {
        "POLICY HEADER",
        "1. PURPOSE",
        "2. ENTITLEMENT",
    }


def test_chunker_splits_large_sections():
    chunker = PolicyChunker(max_chunk_size=50)
    documents = [
        {
            "source": "test_policy.txt",
            "policy_id": "TEST-001",
            "text": "1. DETAILS\n" + ("employee policy guidance " * 12),
        }
    ]

    chunks = chunker.chunk_documents(documents)

    assert len(chunks) > 1
    assert all(len(chunk["text"]) <= 50 for chunk in chunks)
    assert [chunk["id"] for chunk in chunks] == [
        f"TEST-001_{index}" for index in range(len(chunks))
    ]
