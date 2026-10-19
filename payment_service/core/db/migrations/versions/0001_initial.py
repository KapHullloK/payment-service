"""Create tariffs and payments.

Revision ID: 0001_initial
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "tariffs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("price", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("price > 0", name="ck_tariffs_price_positive"),
        sa.UniqueConstraint("title"),
    )
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column(
            "tariff_id", sa.Integer(), sa.ForeignKey("tariffs.id"), nullable=False
        ),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("discount", sa.BigInteger(), nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("installment_months", sa.Integer(), nullable=True),
        sa.Column("schedule", postgresql.ARRAY(sa.BigInteger()), nullable=True),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("amount >= 0", name="ck_payments_amount_nonnegative"),
        sa.CheckConstraint("discount >= 0", name="ck_payments_discount_nonnegative"),
        sa.CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed', 'refunded')",
            name="ck_payments_status",
        ),
        sa.CheckConstraint(
            "method IN ('card', 'sbp', 'installment')", name="ck_payments_method"
        ),
        sa.CheckConstraint(
            "(method = 'installment' AND installment_months IN (3, 6, 12)) OR "
            "(method IN ('card', 'sbp') AND installment_months IS NULL)",
            name="ck_payments_installment_months",
        ),
        sa.UniqueConstraint("idempotency_key"),
    )


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("tariffs")
