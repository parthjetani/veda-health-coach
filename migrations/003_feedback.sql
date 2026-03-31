-- Veda Schema: Add feedback tracking
-- Run after 002_upgrade_schema.sql

create table public.feedback (
    id              uuid primary key default gen_random_uuid(),
    user_id         uuid references public.users(id) on delete set null,
    message_id      text,               -- whatsapp message ID that was rated
    rating          text not null check (rating in ('good', 'bad')),
    reason          text,               -- incorrect / generic / other (null if good)
    user_query      text,               -- the original question
    ai_response     text,               -- the response that was rated
    timestamp       timestamptz not null default now()
);

create index idx_feedback_rating on public.feedback(rating);
create index idx_feedback_ts on public.feedback(timestamp desc);

alter table public.feedback enable row level security;

comment on table public.feedback is 'User feedback on AI responses - drives iteration';
