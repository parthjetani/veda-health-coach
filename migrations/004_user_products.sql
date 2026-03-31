-- Veda Schema: User Products tracking (for footprint, swap priority, progress)
-- Run after 003_feedback.sql

CREATE TABLE public.user_products (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    health_item_id    uuid REFERENCES public.health_items(id) ON DELETE SET NULL,
    product_name      text NOT NULL,
    score             int,
    confidence_source text DEFAULT 'verified' CHECK (confidence_source IN ('verified', 'inferred')),
    still_using       boolean DEFAULT true,
    check_count       int DEFAULT 1,
    first_checked_at  timestamptz DEFAULT now(),
    last_checked_at   timestamptz DEFAULT now()
);

CREATE INDEX idx_user_products_user ON public.user_products(user_id, last_checked_at DESC);
CREATE UNIQUE INDEX idx_user_products_unique ON public.user_products(user_id, product_name);

ALTER TABLE public.user_products ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.user_products IS 'Tracks which products each user has checked. Foundation for footprint, swap priority, and progress features.';
