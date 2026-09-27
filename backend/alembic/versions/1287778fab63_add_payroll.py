"""add payroll

Revision ID: 1287778fab63
Revises: 30708feaa0cc
Create Date: 2026-09-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1287778fab63"
down_revision: Union[str, Sequence[str], None] = "30708feaa0cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ------------------------------------------------------------------
    # Monthly payroll records
    # ------------------------------------------------------------------
    op.create_table(
        "payroll",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "employee_id",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "pay_month",
            sa.String(length=7),
            nullable=False,
        ),
        sa.Column(
            "base_pay_inr",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "bonus_inr",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "deductions_inr",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "net_pay_inr",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "payment_date",
            sa.Date(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.employee_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table("payroll")