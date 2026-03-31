-- Veda Schema: Add user activity tracking for 24h window handling
-- Run after 004_user_products.sql

ALTER TABLE public.users ADD COLUMN IF NOT EXISTS last_active_at timestamptz DEFAULT now();

COMMENT ON COLUMN public.users.last_active_at IS 'Last time user sent a message. Used for 24h WhatsApp window tracking.';
