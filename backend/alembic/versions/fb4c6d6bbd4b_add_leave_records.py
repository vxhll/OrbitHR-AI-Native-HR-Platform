"""add leave records

Revision ID: fb4c6d6bbd4b
Revises: 245fe30695c2
Create Date: 2026-09-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fb4c6d6bbd4b"
down_revision: Union[str, Sequence[str], None] = "245fe30695c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ------------------------------------------------------------------
    # Employee leave records
    # ------------------------------------------------------------------
    op.create_table(
        "leave_records",
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
            "leave_type",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "start_date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "end_date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "days",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "approval_status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "approved_by",
            sa.String(length=20),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.employee_id"],
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["employees.employee_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table("leave_records")