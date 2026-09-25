"""users.referral_count — пересчитать как число оплативших друзей

До этой ревизии referral_count увеличивался ещё и на /start по реферальной
ссылке, поэтому считал приглашённых + оплативших. Теперь его увеличивает
только первая оплата друга (users.referral_bonus_counted); здесь приводим
уже накопленные значения к тому же смыслу. Начисленные ранее дни
(extra_days_granted) не трогаем.

Revision ID: 0016_fix_referral_count
Revises: 0015_bot_content
Create Date: 2026-09-25
"""
from alembic import op

revision = "0016_fix_referral_count"
down_revision = "0015_bot_content"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE users AS u SET referral_count = (
            SELECT count(*) FROM users AS r
            WHERE r.referrer_id = u.telegram_id AND r.referral_bonus_counted
        )
        """
    )


def downgrade() -> None:
    # Прежние (завышенные) значения не восстановить — и не нужно.
    pass
