from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException
from app.security.dependencies import require_employee
from pydantic import BaseModel

from ai.rag.services.rag_service import RAGService


router = APIRouter(
    prefix="/api/rag",
    tags=["RAG"],
)


class RAGQuestion(BaseModel):
    question: str


@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    """Initialize the RAG service only when first requested."""
    return RAGService()



@router.post(
    "/ask",
    dependencies=[Depends(require_employee)],
)
def ask_hr_policy_question(request: RAGQuestion):
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty",
        )

    try:
        rag_service = get_rag_service()

        result = rag_service.ask(
            question=question,
            top_k=3,
        )

        return result

    except Exception:
        # Avoid exposing internal exception details to API clients.
        raise HTTPException(
            status_code=500,
            detail="Unable to process the HR policy question",
        )
