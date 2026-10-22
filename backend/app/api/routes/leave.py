from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.auth.user import User
from app.models.employee import Employee
from app.models.leave_record import LeaveRecord
from app.schemas.leave import (
    LeaveDecisionRequest,
    LeaveRecordResponse,
    LeaveRequestCreate,
)
from app.security.dependencies import (
    get_current_user,
    require_hr,
    require_manager,
)

router = APIRouter(prefix="/api/leave", tags=["Leave Management"])

VALID_LEAVE_TYPES = {
    "Casual Leave",
    "Earned Leave",
    "Sick Leave",
    "Unpaid Leave",
    "Work From Home",
}


def _get_employee_id(current_user: User) -> str:
    if not current_user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not linked to an employee record",
        )
    return str(current_user.employee_id)


def _get_employee(db: Session, employee_id: str) -> Employee:
    employee = db.scalar(
        select(Employee).where(Employee.employee_id == employee_id)
    )
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.get("/my", response_model=list[LeaveRecordResponse])
def get_my_leave(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employee_id = _get_employee_id(current_user)
    return db.scalars(
        select(LeaveRecord)
        .where(LeaveRecord.employee_id == employee_id)
        .order_by(LeaveRecord.start_date.desc(), LeaveRecord.id.desc())
    ).all()


@router.post(
    "/request",
    response_model=LeaveRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_leave_request(
    request: LeaveRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employee_id = _get_employee_id(current_user)

    if request.leave_type not in VALID_LEAVE_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported leave type. Choose one of: {', '.join(sorted(VALID_LEAVE_TYPES))}",
        )

    if request.start_date < date.today():
        raise HTTPException(
            status_code=422,
            detail="Leave requests cannot start in the past",
        )

    _get_employee(db, employee_id)

    days = (request.end_date - request.start_date).days + 1

    leave_record = LeaveRecord(
        employee_id=employee_id,
        leave_type=request.leave_type,
        start_date=request.start_date,
        end_date=request.end_date,
        days=days,
        approval_status="Pending",
        approved_by=None,
    )

    db.add(leave_record)
    db.commit()
    db.refresh(leave_record)
    return leave_record


@router.get("/pending", response_model=list[LeaveRecordResponse])
def get_pending_leave(
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
):
    # Managers can review requests; HR/Admin can review all requests.
    # A manager sees requests for employees assigned to them.
    role = str(current_user.role or "").upper()

    statement = select(LeaveRecord).where(
        LeaveRecord.approval_status == "Pending"
    )

    if role == "MANAGER":
        manager_employee_id = _get_employee_id(current_user)
        statement = statement.join(
            Employee,
            Employee.employee_id == LeaveRecord.employee_id,
        ).where(Employee.manager_id == manager_employee_id)

    return db.scalars(
        statement.order_by(LeaveRecord.start_date, LeaveRecord.id).limit(limit)
    ).all()


@router.patch("/{leave_id}/decision", response_model=LeaveRecordResponse)
def decide_leave_request(
    leave_id: int,
    request: LeaveDecisionRequest,
    current_user: User = Depends(require_hr),
    db: Session = Depends(get_db),
):
    leave_record = db.get(LeaveRecord, leave_id)

    if leave_record is None:
        raise HTTPException(status_code=404, detail="Leave request not found")

    if leave_record.approval_status != "Pending":
        raise HTTPException(
            status_code=409,
            detail="Only pending leave requests can be decided",
        )

    approver_employee_id = _get_employee_id(current_user)
    _get_employee(db, approver_employee_id)

    if leave_record.employee_id == approver_employee_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot approve or reject your own leave request",
        )

    leave_record.approval_status = request.approval_status
    leave_record.approved_by = approver_employee_id

    db.commit()
    db.refresh(leave_record)
    return leave_record
