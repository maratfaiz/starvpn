"""support_ticket_messages — threaded replies instead of one-shot admin_reply;
priority + assignment on support_tickets

Revision ID: 0015_support_ticket_threads
Revises: 0014_referral_redesign
Create Date: 2026-09-03
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_support_ticket_threads"
down_revision = "0014_referral_redesign"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "support_ticket_messages",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "ticket_id", sa.BigInteger(),
            sa.ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("sender", sa.String(16), nullable=False),
        sa.Column("admin_id", sa.BigInteger(), sa.ForeignKey("admin_accounts.id"), nullable=True),
        sa.Column("admin_username", sa.String(64), nullable=True),
        sa.Column("body", sa.String(4000), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_support_ticket_messages_ticket_id", "support_ticket_messages", ["ticket_id"])
    op.create_index("ix_support_ticket_messages_created_at", "support_ticket_messages", ["created_at"])

    op.add_column("support_tickets", sa.Column("priority", sa.String(16), nullable=False, server_default="normal"))
    op.add_column(
        "support_tickets",
        sa.Column("assigned_admin_id", sa.BigInteger(), sa.ForeignKey("admin_accounts.id"), nullable=True),
    )
    op.add_column("support_tickets", sa.Column("last_message_at", sa.DateTime(), nullable=True))
    op.add_column(
        "support_tickets",
        sa.Column("last_message_sender", sa.String(16), nullable=False, server_default="user"),
    )

    # Backfill: the ticket's original text becomes message #1 of the thread.
    op.execute(
        "INSERT INTO support_ticket_messages (ticket_id, sender, body, created_at) "
        "SELECT id, 'user', message, created_at FROM support_tickets"
    )
    # The old single admin_reply (if any) becomes the one admin message so far.
    op.execute(
        "INSERT INTO support_ticket_messages (ticket_id, sender, body, created_at) "
        "SELECT id, 'admin', admin_reply, updated_at FROM support_tickets WHERE admin_reply IS NOT NULL"
    )
    op.execute(
        "UPDATE support_tickets SET last_message_at = updated_at, "
        "last_message_sender = CASE WHEN admin_reply IS NOT NULL THEN 'admin' ELSE 'user' END"
    )
    op.alter_column("support_tickets", "last_message_at", nullable=False)
    op.drop_column("support_tickets", "admin_reply")


def downgrade() -> None:
    op.add_column("support_tickets", sa.Column("admin_reply", sa.String(4000), nullable=True))
    op.execute(
        "UPDATE support_tickets t SET admin_reply = ("
        "SELECT body FROM support_ticket_messages m "
        "WHERE m.ticket_id = t.id AND m.sender = 'admin' "
        "ORDER BY m.created_at DESC LIMIT 1)"
    )
    op.drop_column("support_tickets", "last_message_sender")
    op.drop_column("support_tickets", "last_message_at")
    op.drop_column("support_tickets", "assigned_admin_id")
    op.drop_column("support_tickets", "priority")
    op.drop_table("support_ticket_messages")
