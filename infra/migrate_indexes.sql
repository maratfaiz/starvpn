-- STAR VPN — migration: add missing indexes and FK
-- Run inside the DB container:
--   docker compose exec db psql -U starvpn -d starvpn -f /migrate_indexes.sql

-- Index on users.referrer_id (needed for referral queries)
CREATE INDEX IF NOT EXISTS ix_users_referrer_id ON users (referrer_id);

-- Index on payments.status (needed for paid-invoice lookups)
CREATE INDEX IF NOT EXISTS ix_payments_status ON payments (status);

-- FK + CASCADE on gift_notifications.recipient_id
ALTER TABLE gift_notifications
    ADD CONSTRAINT IF NOT EXISTS fk_gift_recipient
    FOREIGN KEY (recipient_id)
    REFERENCES users (telegram_id)
    ON DELETE CASCADE;
