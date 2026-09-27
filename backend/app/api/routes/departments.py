from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.department import Department
from app.models.employee import Employee


router = APIRouter(
    prefix="/api/departments",
    tags=["Departments"],
)


@router.get("")
def get_departments(db: Session = Depends(get_db)):
    departments = db.scalars(
        select(Department).order_by(Department.name)
    ).all()

    return {
        "count": len(departments),
        "departments": [
            {
                "id": department.id,
                "name": department.name,
                "organization_id": department.organization_id,
            }
            for department in departments
        ],
    }


@router.get("/{department_id}")
def get_department(
    department_id: int,
    db: Session = Depends(get_db),
):
    department = db.scalar(
        select(Department).where(Department.id == department_id)
    )

    if department is None:
        raise HTTPException(
            status_code=404,
            detail=f"Department {department_id} not found",
        )

    employee_count = db.scalar(
        select(func.count(Employee.id)).where(
            Employee.department_id == department_id
        )
    )

    return {
        "id": department.id,
        "name": department.name,
        "organization_id": department.organization_id,
        "employee_count": employee_count or 0,
    }


@router.get("/{department_id}/employees")
def get_department_employees(
    department_id: int,
    db: Session = Depends(get_db),
):
    department = db.scalar(
        select(Department).where(Department.id == department_id)
    )

    if department is None:
        raise HTTPException(
            status_code=404,
            detail=f"Department {department_id} not found",
        )

    employees = db.scalars(
        select(Employee)
        .where(Employee.department_id == department_id)
        .order_by(Employee.employee_id)
    ).all()

    return {
        "department": {
            "id": department.id,
            "name": department.name,
        },
        "count": len(employees),
        "employees": [
            {
                "employee_id": employee.employee_id,
                "full_name": employee.full_name,
                "job_role": employee.job_role,
                "job_level": employee.job_level,
                "work_location": employee.work_location,
            }
            for employee in employees
        ],
    }