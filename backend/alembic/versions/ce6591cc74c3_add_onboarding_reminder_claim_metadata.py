
"""add onboarding reminder claim metadata

Revision ID: ce6591cc74c3
Revises: e135b6694aa8
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ce6591cc74c3"
down_revision: Union[str, Sequence[str], None] = "e135b6694aa8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "onboarding_reminders",
        sa.Column("claim_token", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "onboarding_reminders",
        sa.Column("claimed_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("onboarding_reminders", "claimed_at")
    op.drop_column("onboarding_reminders", "claim_token")
