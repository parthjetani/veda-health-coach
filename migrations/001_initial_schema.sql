-- Veda AI Health Coach - Supabase Schema (Full)
-- Run this in Supabase SQL Editor for a fresh install
-- For existing installs, run 002_upgrade_schema.sql instead

-- Enable fuzzy text search extension
create extension if not exists pg_trgm;

-----------------------------------------------------------
-- USERS
-----------------------------------------------------------
create table public.users (
    id                  uuid primary key default gen_random_uuid(),
    whatsapp_number     text unique not null,       -- E.164 format: +1234567890
    stripe_customer_id  text unique,
    is_active           boolean not null default true,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);

comment on table public.users is 'WhatsApp users with subscription status';

-----------------------------------------------------------
-- CONVERSATIONS
-----------------------------------------------------------
create table public.conversations (
    id              uuid primary key default gen_random_uuid(),
    user_id         uuid not null references public.users(id) on delete cascade,
    role            text not null check (role in ('user', 'assistant')),
    message_text    text not null,
    whatsapp_msg_id text unique,
    metadata        jsonb default '{}'::jsonb,      -- intent, verdict, confidence, kb_match
    timestamp       timestamptz not null default now()
);

create index idx_conversations_user_ts on public.conversations(user_id, timestamp desc);

comment on table public.conversations is 'Chat history with analytics metadata';

-----------------------------------------------------------
-- HEALTH ITEMS (Knowledge Base)
-----------------------------------------------------------
create table public.health_items (
    id                  uuid primary key default gen_random_uuid(),
    item_name           text not null,
    brand               text,
    category            text check (category in ('food', 'supplement', 'personal_care', 'household', 'other')),
    ingredients         jsonb not null default '[]'::jsonb,         -- full ingredient list from label
    flagged_ingredients jsonb not null default '[]'::jsonb,         -- [{name, reason, risk}]
    risk_level          text check (risk_level in ('high', 'medium', 'low')),
    recommendation      text,
    alternative_brand   text,
    aliases             text[] default '{}',                        -- search synonyms
    confidence_source   text not null default 'verified'
                        check (confidence_source in ('verified', 'inferred', 'community')),
    barcode             text,
    ewg_rating          text,
    notes               text,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);

-- Search indexes
create index idx_health_items_name_trgm on public.health_items using gin (item_name gin_trgm_ops);
create index idx_health_items_brand_trgm on public.health_items using gin (brand gin_trgm_ops);
create index idx_health_items_aliases on public.health_items using gin (aliases);

comment on table public.health_items is 'Curated product knowledge base';

-----------------------------------------------------------
-- UNKNOWN QUERIES (Curation Queue)
-----------------------------------------------------------
create table public.unknown_queries (
    id              uuid primary key default gen_random_uuid(),
    user_id         uuid references public.users(id) on delete set null,
    query_text      text not null,
    resolved        boolean not null default false,
    resolved_item_id uuid references public.health_items(id) on delete set null,
    timestamp       timestamptz not null default now()
);

comment on table public.unknown_queries is 'Products users asked about that were not in the knowledge base';

-----------------------------------------------------------
-- SEARCH FUNCTION (fuzzy + substring + alias matching)
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
            coalesce((
                select max(similarity(lower(alias), lower(query)))
                from unnest(hi.aliases) as alias
            ), 0)
        ) as similarity_score
    from public.health_items hi
    where
        similarity(lower(hi.item_name), lower(query)) > match_threshold
        or similarity(lower(coalesce(hi.brand, '')), lower(query)) > match_threshold
        or lower(query) like '%' || lower(hi.item_name) || '%'
        or lower(hi.item_name) like '%' || lower(query) || '%'
        or exists (
            select 1 from unnest(hi.aliases) as alias
            where similarity(lower(alias), lower(query)) > match_threshold
            or lower(query) like '%' || lower(alias) || '%'
        )
    order by similarity_score desc
    limit 5;
$$;

-----------------------------------------------------------
-- ROW LEVEL SECURITY
-----------------------------------------------------------
alter table public.users enable row level security;
alter table public.conversations enable row level security;
alter table public.health_items enable row level security;
alter table public.unknown_queries enable row level security;

-----------------------------------------------------------
-- UPDATED_AT TRIGGER
-----------------------------------------------------------
create or replace function update_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger users_updated_at
    before update on public.users
    for each row execute function update_updated_at();

create trigger health_items_updated_at
    before update on public.health_items
    for each row execute function update_updated_at();
