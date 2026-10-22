from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from datetime import date
from sqlalchemy import or_, select
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.agents.onboarding.agent import OnboardingAgent
from app.db.database import get_db
from app.models.auth.user import User
from app.models.onboarding import OnboardingCase, OnboardingTask, OnboardingDocument
from app.schemas.onboarding import (
    OnboardingCaseCreate,
    OnboardingCaseResponse,
    OnboardingDocumentResponse,
    OnboardingDocumentVerificationRequest,
    OnboardingTaskResponse,
    OnboardingDocumentProgressResponse,
    OnboardingReadinessResponse,
)
from app.security.dependencies import get_current_user, require_hr
from app.services.onboarding_service import OnboardingService


router = APIRouter(
    prefix="/api/onboarding",
    tags=["Onboarding"],
)


def get_authorized_case(
    db: Session,
    onboarding_case_id: int,
    current_user: User,
) -> OnboardingCase:
    onboarding_case = OnboardingService.get_onboarding_case(
        db=db,
        onboarding_case_id=onboarding_case_id,
    )

    if onboarding_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding case not found",
        )

    role = current_user.role.upper()

    if role not in {"HR", "ADMIN"}:
        if current_user.employee_id != onboarding_case.employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own onboarding case",
            )

    return onboarding_case


def get_authorized_task(
    db: Session,
    task_id: int,
    current_user: User,
) -> OnboardingTask:
    task = db.get(OnboardingTask, task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding task not found",
        )

    get_authorized_case(
        db=db,
        onboarding_case_id=task.onboarding_case_id,
        current_user=current_user,
    )

    return task


def get_authorized_document(
    db: Session,
    document_id: int,
    current_user: User,
) -> OnboardingDocument:
    document = db.get(OnboardingDocument, document_id)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding document not found",
        )

    get_authorized_case(
        db=db,
        onboarding_case_id=document.onboarding_case_id,
        current_user=current_user,
    )

    return document


@router.post(
    "",
    response_model=OnboardingCaseResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_hr)],
)
def create_onboarding_case(
    onboarding_data: OnboardingCaseCreate,
    db: Session = Depends(get_db),
):
    try:
        return OnboardingService.create_onboarding_case(
            db=db,
            employee_id=onboarding_data.employee_id,
            candidate_id=onboarding_data.candidate_id,
            joining_date=onboarding_data.joining_date,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/{onboarding_case_id}",
    response_model=OnboardingCaseResponse,
)
def get_onboarding_case(
    onboarding_case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_authorized_case(db, onboarding_case_id, current_user)


@router.get(
    "/{onboarding_case_id}/tasks",
    response_model=list[OnboardingTaskResponse],
)
def get_onboarding_tasks(
    onboarding_case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_authorized_case(db, onboarding_case_id, current_user)

    return OnboardingService.get_tasks(
        db=db,
        onboarding_case_id=onboarding_case_id,
    )


@router.get(
    "/{onboarding_case_id}/documents",
    response_model=list[OnboardingDocumentResponse],
)
def get_onboarding_documents(
    onboarding_case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_authorized_case(db, onboarding_case_id, current_user)

    return OnboardingService.get_documents(
        db=db,
        onboarding_case_id=onboarding_case_id,
    )


@router.post(
    "/tasks/{task_id}/complete",
    response_model=OnboardingTaskResponse,
)
def complete_onboarding_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_authorized_task(db, task_id, current_user)

    task = OnboardingService.complete_task(
        db=db,
        task_id=task_id,
    )

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding task not found",
        )

    return task


@router.post(
    "/documents/{document_id}/upload",
    response_model=OnboardingDocumentResponse,
)
async def upload_onboarding_document(
    document_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_authorized_document(db, document_id, current_user)

    try:
        file_content = await file.read()

        return OnboardingService.submit_document(
            db=db,
            document_id=document_id,
            file_name=file.filename or "uploaded_file",
            file_content=file_content,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/documents/{document_id}/verify",
    response_model=OnboardingDocumentResponse,
    dependencies=[Depends(require_hr)],
)
def verify_onboarding_document(
    document_id: int,
    request: OnboardingDocumentVerificationRequest,
    db: Session = Depends(get_db),
):
    try:
        document = OnboardingService.verify_document(
            db=db,
            document_id=document_id,
            status=request.status,
        )

        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Onboarding document not found",
            )

        return document
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/{onboarding_case_id}/documents/progress",
    response_model=OnboardingDocumentProgressResponse,
)
def get_onboarding_document_progress(
    onboarding_case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_authorized_case(db, onboarding_case_id, current_user)

    return OnboardingService.get_document_progress(
        db=db,
        onboarding_case_id=onboarding_case_id,
    )


@router.get(
    "/{onboarding_case_id}/readiness",
    response_model=OnboardingReadinessResponse,
)
def get_onboarding_readiness(
    onboarding_case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_authorized_case(db, onboarding_case_id, current_user)

    return OnboardingService.get_onboarding_readiness(
        db=db,
        onboarding_case_id=onboarding_case_id,
    )


@router.get("/{onboarding_case_id}/recommendations")
def get_onboarding_recommendations(
    onboarding_case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_authorized_case(db, onboarding_case_id, current_user)

    agent = OnboardingAgent()
    return agent.get_recommendations(
        db=db,
        onboarding_case_id=onboarding_case_id,
    )

@router.get(
    "/automation/overdue-tasks",
    dependencies=[Depends(require_hr)],
)
def get_overdue_onboarding_tasks(
    db: Session = Depends(get_db),
):
    today = date.today()

    result = db.execute(
        select(OnboardingTask, OnboardingCase)
        .join(
            OnboardingCase,
            OnboardingTask.onboarding_case_id == OnboardingCase.id,
        )
        .where(
            OnboardingTask.due_date < today,
            OnboardingTask.status != "Completed",
            OnboardingCase.status != "Completed",
        )
        .order_by(
            OnboardingTask.due_date.asc(),
            OnboardingTask.id.asc(),
        )
    )

    rows = result.all()

    tasks = [
        {
            "task_id": task.id,
            "onboarding_case_id": task.onboarding_case_id,
            "employee_id": case.employee_id,
            "task_code": task.task_code,
            "title": task.title,
            "status": task.status,
            "due_date": task.due_date,
            "days_overdue": (today - task.due_date).days,
            "required": task.required,
        }
        for task, case in rows
    ]

    return {
        "generated_on": today,
        "total_overdue_tasks": len(tasks),
        "tasks": tasks,
    }