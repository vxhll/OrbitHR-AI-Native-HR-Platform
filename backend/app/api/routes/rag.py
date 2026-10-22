from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ai.rag.services.rag_service import RAGService


router = APIRouter(
    prefix="/api/rag",
    tags=["RAG"],
)


class RAGQuestion(BaseModel):
    question: str


rag_service = RAGService()


@router.post("/ask")
def ask_hr_policy_question(request: RAGQuestion):

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty",
        )

    try:
        result = rag_service.ask(
            question=question,
            top_k=3,
        )

        return result

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"RAG service error: {str(exc)}",
        )