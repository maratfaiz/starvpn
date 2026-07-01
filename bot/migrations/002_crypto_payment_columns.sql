-- Migration 002: Add crypto payment columns to payments table
-- Run once on the server:
--   docker exec -e PGPASSWORD='Str0ngP@ssw0rd_STAR2026!' infra-db-1 \
--     psql -U starvpn -d starvpn -f /path/to/this_file.sql

ALTER TABLE payments
  ADD COLUMN IF NOT EXISTS payment_method VARCHAR(16) NOT NULL DEFAULT 'stars',
  ADD COLUMN IF NOT EXISTS asset          VARCHAR(16),
  ADD COLUMN IF NOT EXISTS invoice_id     BIGINT,
  ADD COLUMN IF NOT EXISTS days           INTEGER;

CREATE INDEX IF NOT EXISTS ix_payments_invoice_id ON payments(invoice_id);
