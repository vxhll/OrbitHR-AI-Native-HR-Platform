"""add attrition records

Revision ID: 554b0e0bee87
Revises: eda3c39fc7e7
Create Date: 2026-09-26 19:45:30.221205

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "554b0e0bee87"
down_revision: Union[str, Sequence[str], None] = "eda3c39fc7e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ------------------------------------------------------------------
    # Attrition records
    # ------------------------------------------------------------------
    op.create_table(
        "attrition_records",
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
            "employment_status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "exit_date",
            sa.Date(),
            nullable=True,
        ),
        sa.Column(
            "exit_type",
            sa.String(length=30),
            nullable=True,
        ),
        sa.Column(
            "exit_reason",
            sa.String(length=200),
            nullable=True,
        ),
        sa.Column(
            "notice_period_days",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "rehire_eligible",
            sa.Boolean(),
            nullable=True,
        ),
        sa.Column(
            "attrited_within_180_days_label",
            sa.Integer(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.employee_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "employee_id",
            name="uq_attrition_records_employee_id",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table("attrition_records")