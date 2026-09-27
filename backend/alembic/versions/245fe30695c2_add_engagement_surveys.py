"""add engagement surveys

Revision ID: 245fe30695c2
Revises: f77b52a93c74
Create Date: 2026-09-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "245fe30695c2"
down_revision: Union[str, Sequence[str], None] = "f77b52a93c74"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ------------------------------------------------------------------
    # Monthly employee engagement survey records
    # ------------------------------------------------------------------
    op.create_table(
        "engagement_surveys",
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
            "survey_period",
            sa.String(length=7),
            nullable=False,
        ),
        sa.Column(
            "engagement_score_1to10",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "job_satisfaction_score_1to10",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "employee_nps",
            sa.Integer(),
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

    op.drop_table("engagement_surveys")