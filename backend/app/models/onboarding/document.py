from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class OnboardingDocument(Base):
    __tablename__ = "onboarding_documents"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    onboarding_case_id: Mapped[int] = mapped_column(
        ForeignKey("onboarding_cases.id"),
        nullable=False,
    )

    document_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="Pending",
    )

    file_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )