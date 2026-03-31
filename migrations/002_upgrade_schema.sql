-- Veda Schema Upgrade: Portfolio -> Production Foundation
-- Run this AFTER schema.sql has been applied
-- Supabase Dashboard -> SQL Editor -> New Query -> Paste -> Run

-----------------------------------------------------------
-- HEALTH ITEMS: Add new columns
-----------------------------------------------------------

-- Full ingredient list (the complete label, not just flagged ones)
alter table public.health_items
    add column if not exists ingredients jsonb default '[]'::jsonb;

-- Structured flagged ingredients: [{name, reason, risk}]
-- Migration: rename old flat array column, add new structured one
alter table public.health_items
    rename column flagged_ingredients to flagged_ingredients_legacy;

alter table public.health_items
    add column flagged_ingredients jsonb not null default '[]'::jsonb;

comment on column public.health_items.flagged_ingredients is
    'Structured array: [{"name": "Fragrance", "reason": "may irritate skin", "risk": "medium"}]';

comment on column public.health_items.ingredients is
    'Full ingredient list from the product label';

-- Aliases for fuzzy matching (e.g., ["dove soap", "dove bar", "dove beauty bar"])
alter table public.health_items
    add column if not exists aliases text[] default '{}';

-- Data source tracking
alter table public.health_items
    add column if not exists confidence_source text not null default 'verified'
    check (confidence_source in ('verified', 'inferred', 'community'));

comment on column public.health_items.confidence_source is
    'verified = manually curated, inferred = AI-generated, community = user-submitted';

-- Trigram index on aliases for search
create index if not exists idx_health_items_aliases
    on public.health_items using gin (aliases);

-----------------------------------------------------------
-- CONVERSATIONS: Add metadata for analytics
-----------------------------------------------------------

alter table public.conversations
    add column if not exists metadata jsonb default '{}'::jsonb;

comment on column public.conversations.metadata is
    'Stores intent type, verdict, confidence, kb_match for analytics and debugging';

-----------------------------------------------------------
-- UNKNOWN QUERIES: Add resolution tracking
-----------------------------------------------------------

alter table public.unknown_queries
    add column if not exists resolved boolean not null default false;

alter table public.unknown_queries
    add column if not exists resolved_item_id uuid references public.health_items(id) on delete set null;

comment on column public.unknown_queries.resolved is
    'Set to true when the product has been added to health_items';

-----------------------------------------------------------
-- UPGRADE SEARCH FUNCTION
-- Now searches: item_name, brand, aliases, AND substring match
-----------------------------------------------------------

create or replace function search_health_items(
    query text,
    match_threshold float default 0.3
)
returns table (
    id                  uuid,
    item_name           text,
    brand               text,
    category            text,
    ingredients         jsonb,
    flagged_ingredients jsonb,
    risk_level          text,
    recommendation      text,
    alternative_brand   text,
    aliases             text[],
    confidence_source   text,
    notes               text,
    similarity_score    float
)
language sql stable
as $$
    select
        hi.id,
        hi.item_name,
        hi.brand,
        hi.category,
        hi.ingredients,
        hi.flagged_ingredients,
        hi.risk_level,
        hi.recommendation,
        hi.alternative_brand,
        hi.aliases,
        hi.confidence_source,
        hi.notes,
        greatest(
            similarity(lower(hi.item_name), lower(query)),
            similarity(lower(coalesce(hi.brand, '')), lower(query)),
            -- Check aliases: find best match across all aliases
            coalesce((
                select max(similarity(lower(alias), lower(query)))
                from unnest(hi.aliases) as alias
            ), 0)
        ) as similarity_score
    from public.health_items hi
    where
        -- Trigram fuzzy match on name
        similarity(lower(hi.item_name), lower(query)) > match_threshold
        -- Trigram fuzzy match on brand
        or similarity(lower(coalesce(hi.brand, '')), lower(query)) > match_threshold
        -- Exact substring match (catches "dove soap" in "is dove soap safe")
        or lower(query) like '%' || lower(hi.item_name) || '%'
        or lower(hi.item_name) like '%' || lower(query) || '%'
        -- Alias match
        or exists (
            select 1 from unnest(hi.aliases) as alias
            where similarity(lower(alias), lower(query)) > match_threshold
            or lower(query) like '%' || lower(alias) || '%'
        )
    order by similarity_score desc
    limit 5;
$$;

-----------------------------------------------------------
-- MIGRATE EXISTING DATA
-- Convert flat flagged_ingredients to structured format
-----------------------------------------------------------

-- This converts ["Fragrance", "Parabens"] to [{"name": "Fragrance"}, {"name": "Parabens"}]
update public.health_items
set flagged_ingredients = (
    select coalesce(
        jsonb_agg(jsonb_build_object('name', elem)),
        '[]'::jsonb
    )
    from jsonb_array_elements_text(flagged_ingredients_legacy) as elem
)
where flagged_ingredients_legacy != '[]'::jsonb
  and flagged_ingredients_legacy is not null;
