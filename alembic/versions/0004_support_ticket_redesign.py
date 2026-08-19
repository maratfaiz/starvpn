"""support_tickets — anonymous submissions (no login required), topic instead of subject

Revision ID: 0004_support_ticket_redesign
Revises: 0003_ban_reason
Create Date: 2026-08-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_support_ticket_redesign"
down_revision = "0003_ban_reason"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("support_tickets", "user_id", nullable=True)
    op.add_column("support_tickets", sa.Column("contact", sa.String(320), nullable=True))
    op.add_column("support_tickets", sa.Column("topic", sa.String(32), nullable=False, server_default="other"))
    op.execute("UPDATE support_tickets SET contact = subject WHERE contact IS NULL")
    op.drop_column("support_tickets", "subject")


def downgrade() -> None:
    op.add_column("support_tickets", sa.Column("subject", sa.String(200), nullable=False, server_default="—"))
    op.drop_column("support_tickets", "topic")
    op.drop_column("support_tickets", "contact")
    op.alter_column("support_tickets", "user_id", nullable=False)
