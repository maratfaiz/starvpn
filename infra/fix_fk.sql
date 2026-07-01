DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_gift_recipient'
  ) THEN
    ALTER TABLE gift_notifications
      ADD CONSTRAINT fk_gift_recipient
      FOREIGN KEY (recipient_id)
      REFERENCES users (telegram_id)
      ON DELETE CASCADE;
  END IF;
END $$;
