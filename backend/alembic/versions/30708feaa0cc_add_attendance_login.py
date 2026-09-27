"""add attendance login

Revision ID: 30708feaa0cc
Revises: 554b0e0bee87
Create Date: 2026-09-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "30708feaa0cc"
down_revision: Union[str, Sequence[str], None] = "554b0e0bee87"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ------------------------------------------------------------------
    # Daily attendance and login records
    # ------------------------------------------------------------------
    op.create_table(
        "attendance_login",
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
            "date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "login_time",
            sa.Time(),
            nullable=True,
        ),
        sa.Column(
            "logout_time",
            sa.Time(),
            nullable=True,
        ),
        sa.Column(
            "hours_worked",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.employee_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table("attendance_login")