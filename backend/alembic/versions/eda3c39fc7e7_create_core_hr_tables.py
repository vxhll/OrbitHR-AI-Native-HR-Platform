"""create core HR tables

Revision ID: eda3c39fc7e7
Revises:
Create Date: 2026-09-26 19:34:55.894885

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "eda3c39fc7e7"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ------------------------------------------------------------------
    # Organizations
    # ------------------------------------------------------------------
    op.create_table(
        "organizations",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=150),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # ------------------------------------------------------------------
    # Departments
    # ------------------------------------------------------------------
    op.create_table(
        "departments",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------
    # Employees
    # ------------------------------------------------------------------
    # IMPORTANT:
    # manager_id references employees.employee_id.
    # PostgreSQL requires the referenced column to have a UNIQUE
    # constraint before the foreign key can be created.
    #
    # Therefore:
    # 1. Create employees without the self-referencing FK.
    # 2. Create UNIQUE(employee_id).
    # 3. Create the self-referencing FK.
    # ------------------------------------------------------------------
    op.create_table(
        "employees",
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
            "full_name",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "gender",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "age",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "department_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "job_role",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "job_level",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "work_location",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "hire_date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "tenure_years_at_period_start",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
        ),
        sa.Column(
            "education",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "marital_status",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "annual_base_salary_inr",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "manager_id",
            sa.String(length=20),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # employee_id must be unique because manager_id references it.
    op.create_unique_constraint(
        "uq_employees_employee_id",
        "employees",
        ["employee_id"],
    )

    # Self-referencing manager relationship.
    op.create_foreign_key(
        "fk_employees_manager_id",
        "employees",
        "employees",
        ["manager_id"],
        ["employee_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""

    # Remove the self-referencing FK first.
    op.drop_constraint(
        "fk_employees_manager_id",
        "employees",
        type_="foreignkey",
    )

    # Remove employee_id uniqueness.
    op.drop_constraint(
        "uq_employees_employee_id",
        "employees",
        type_="unique",
    )

    # Drop tables in dependency order.
    op.drop_table("employees")
    op.drop_table("departments")
    op.drop_table("organizations")