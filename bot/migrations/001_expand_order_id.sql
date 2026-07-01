-- Migration 001: expand payments.order_id from VARCHAR(64) to VARCHAR(255)
-- Reason: Telegram Stars charge_id can exceed 130 characters,
--         causing StringDataRightTruncationError on every successful payment.
--
-- Run once on the server:
--   docker exec -i infra-postgres-1 psql -U $POSTGRES_USER -d $POSTGRES_DB < 001_expand_order_id.sql

ALTER TABLE payments
    ALTER COLUMN order_id TYPE VARCHAR(255);
