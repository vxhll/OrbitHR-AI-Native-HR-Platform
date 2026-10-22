
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.employee_support.graph import employee_support_graph
from app.db.database import get_db
from app.models.auth.user import User
from app.security.dependencies import get_current_user
from app.schemas.support.ask import (
    HRSupportQuestion,
    HRSupportResponse,
)


router = APIRouter(
    prefix="/api/support",
    tags=["Employee Support"],
)


def _resolve_onboarding_case(
    db: Session,
    onboarding_case_id: int,
    current_user: User,
) -> int:
    """Authorize the requested onboarding case and return its ID."""

    from app.models.onboarding import OnboardingCase

    onboarding_case = db.get(
        OnboardingCase,
        onboarding_case_id,
    )

    if onboarding_case is None:
        raise HTTPException(
            status_code=404,
            detail="Onboarding case not found",
        )

    role = str(current_user.role or "").upper()

    if role not in {"HR", "ADMIN"}:
        if (
            not current_user.employee_id
            or str(current_user.employee_id)
            != str(onboarding_case.employee_id)
        ):
            raise HTTPException(
                status_code=403,
                detail="You can only access your own onboarding case",
            )

    return onboarding_case.id


@router.post(
    "/ask",
    response_model=HRSupportResponse,
)
def ask_hr_support(
    request: HRSupportQuestion,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        role = str(current_user.role or "").upper()

        # Employees remain restricted to their own employee ID.
        # HR/Admin may specify a target for authorized support requests.
        if role in {"HR", "ADMIN"}:
            employee_id = (
                request.employee_id or current_user.employee_id
            )
        else:
            employee_id = current_user.employee_id

            if not employee_id:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Your account is not linked to an employee record"
                    ),
                )

            if (
                request.employee_id
                and request.employee_id != employee_id
            ):
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "You cannot request another employee's information"
                    ),
                )

        onboarding_case_id = request.onboarding_case_id

        # Validate case ownership before the graph can access onboarding data.
        if onboarding_case_id is not None:
            onboarding_case_id = _resolve_onboarding_case(
                db=db,
                onboarding_case_id=onboarding_case_id,
                current_user=current_user,
            )

        result = employee_support_graph.invoke(
            {
                "question": request.question,
                "employee_id": employee_id,
                "onboarding_case_id": onboarding_case_id,
                "prediction_date": (
                    request.prediction_date.isoformat()
                    if request.prediction_date
                    else None
                ),
            }
        )

        return {
            "question": request.question,
            "intent": result.get("intent", "UNKNOWN"),
            "confidence": result.get("confidence", 0.0),
            "answer": result.get(
                "answer",
                "Unable to generate a response.",
            ),
            "requires_human": result.get(
                "requires_human",
                False,
            ),
            "sources": result.get("sources", []),
        }

    except HTTPException:
        raise

    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail=(
                "The HR support service is temporarily unavailable."
            ),
        ) from None

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to process the HR support request.",
        ) from None
