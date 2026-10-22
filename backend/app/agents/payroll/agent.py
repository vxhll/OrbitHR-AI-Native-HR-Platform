from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payroll import Payroll
from app.models.employee import Employee


class PayrollAgent:
    """
    Read-only payroll support agent.

    The agent retrieves payroll information for a specific employee
    and formats it into an employee-friendly response.
    """

    def get_latest_payroll(
        self,
        db: Session,
        employee_id: str,
    ) -> dict:

        employee = db.scalar(
            select(Employee).where(
                Employee.employee_id == employee_id
            )
        )

        if employee is None:
            return {
                "answer": f"Employee {employee_id} could not be found.",
                "sources": [],
                "requires_human": False,
            }

        payroll = db.scalars(
            select(Payroll)
            .where(
                Payroll.employee_id == employee_id
            )
            .order_by(Payroll.pay_month.desc())
        ).first()

        if payroll is None:
            return {
                "answer": (
                    f"No payroll records were found for "
                    f"employee {employee_id}."
                ),
                "sources": [],
                "requires_human": False,
            }

        answer = (
            f"Your latest payroll record is for {payroll.pay_month}. "
            f"Base pay: ₹{payroll.base_pay_inr:,}. "
            f"Bonus: ₹{payroll.bonus_inr:,}. "
            f"Deductions: ₹{payroll.deductions_inr:,}. "
            f"Net pay: ₹{payroll.net_pay_inr:,}. "
            f"Payment date: {payroll.payment_date}."
        )

        return {
            "answer": answer,
            "sources": [
                {
                    "type": "payroll",
                    "employee_id": employee_id,
                    "pay_month": payroll.pay_month,
                    "payroll_id": payroll.id,
                }
            ],
            "requires_human": False,
        }