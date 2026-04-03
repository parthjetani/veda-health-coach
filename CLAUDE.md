# CLAUDE.md - Veda AI Health Coach

## Project

Veda is a production-grade WhatsApp AI health coaching chatbot. Users check products, get a 0-100 verdict score, track their chemical exposure over time, and get personalized swap recommendations. Built with Python/FastAPI + Google Gemini + Supabase + WhatsApp Cloud API.

## Commands

```bash
# Run dev server
uvicorn app.main:app --reload --port 8000

# Run tests (153 tests)
./venv/Scripts/python -m pytest tests/ -v

# Seed products to database
./venv/Scripts/python scripts/seed_health_items.py

# Seed with specific file
./venv/Scripts/python scripts/seed_health_items.py --file seed_india_products.json

# Update existing products
./venv/Scripts/python scripts/seed_health_items.py --update
```

## Tech Stack

- **Backend**: Python 3.12, FastAPI, uvicorn
- **AI**: Google Gemini 2.5 Flash (`google-genai`) with structured JSON output via `response_schema`
- **Database**: Supabase (PostgreSQL + pg_trgm fuzzy search)
- **Messaging**: WhatsApp Cloud API (Meta Graph API)
- **Testing**: pytest, pytest-asyncio, respx
- **Virtual env**: `./venv/` (always use `./venv/Scripts/python` on Windows)

## Architecture

```
User message -> POST /webhook/whatsapp -> BackgroundTask:
  0. Verify X-Hub-Signature-256 (optional, skipped if WHATSAPP_APP_SECRET empty)
  1. Rate limit check (30/user/hour)
  2. Command router:
     - "my footprint" -> footprint.py (bypass AI)
     - "what should I swap" -> swap_priority.py (bypass AI)
     - "compare X vs Y" -> product_comparison.py (bypass AI)
  3. KB lookup (fuzzy + alias + substring, skip if query < 4 chars)
  4. Calculate score (deterministic, 0-100)
  5. Auto-save to user_products + auto-insert inferred to health_items
  6. Call Gemini API (8s timeout, retry once, structured JSON)
  7. Format response + score + progress + EWG rating
  8. Send reply + feedback buttons (24h window fallback to template)
```

## Key Directories

- `app/core/` - Business logic: message_handler (orchestrator), product_scorer, footprint, swap_priority, product_comparison, daily_tips, response_formatter, feedback_handler, errors
- `app/services/` - External integrations: ai_engine (Gemini), whatsapp_client, knowledge_base, source_context, conversation
- `app/db/queries/` - Supabase queries: users, health_items, user_products, conversations, feedback, analytics, unknown_queries
- `app/api/` - HTTP endpoints: webhooks/whatsapp, admin/* (CRUD + analytics + footprint)
- `app/models/` - Pydantic: whatsapp.py (webhook payload), ai_response.py (AI response schema), admin.py (API models)
- `prompts/` - System prompt loaded at startup (health_coach.txt)
- `migrations/` - 5 SQL files (001-005), run manually in Supabase SQL Editor
- `scripts/` - Seed data (seed_health_items.py + JSON files)

## Important Patterns

### Always return 200 to WhatsApp webhook
Meta retries on non-200. Process in `BackgroundTasks`, never block the response.

### Supabase client via app.state
```python
# Initialized in main.py lifespan
app.state.supabase = create_client(url, key)
# Accessed via request.app.state.supabase in endpoints
```

### Use .limit(1) not .maybe_single()
Supabase Python client crashes with `maybe_single()` on empty results. Always use `.limit(1)` and check `result.data`.

### Scoring is deterministic (no AI)
`product_scorer.py` deducts points per flagged ingredient: high=-30, medium=-15, low=-5. Never pass scoring to the LLM.

### Special commands bypass AI
"my footprint" and "what should I swap" are handled by `footprint.py` and `swap_priority.py` directly. No Gemini call. Faster and cheaper.

### Structured JSON enforced at API level
Gemini's `response_mime_type="application/json"` + `response_schema` forces exact JSON structure. The response_formatter has a fallback that strips markdown if JSON parsing fails.

### Config ignores extra env vars
`Settings` uses `extra="ignore"` so old/unused env vars in `.env` don't crash the app.

### All admin endpoints require X-API-Key header
Validated via `app/core/security.py` dependency.

## Environment Variables

Required:
- `WHATSAPP_ACCESS_TOKEN` - Meta System User token
- `WHATSAPP_PHONE_NUMBER_ID` - From Meta Business Suite
- `WHATSAPP_VERIFY_TOKEN` - Any random string (shared with Meta webhook config)
- `GEMINI_API_KEY` - From aistudio.google.com
- `SUPABASE_URL` - https://xxx.supabase.co
- `SUPABASE_SERVICE_ROLE_KEY` - service_role key (NOT anon)
- `ADMIN_API_KEY` - Long random string
- `WHATSAPP_APP_SECRET` - From Meta App Dashboard (Settings > Basic > App Secret). Required for webhook signature verification in production. Optional in dev (skipped if empty).

Optional (have defaults):
- `GEMINI_MODEL` (default: gemini-2.5-flash)
- `GEMINI_MAX_TOKENS` (default: 1024)
- `GEMINI_TEMPERATURE` (default: 0.3)
- `WHATSAPP_API_VERSION` (default: v21.0)
- `ENVIRONMENT` (default: development)
- `CORS_ORIGINS` (default: *) - Comma-separated allowed origins for CORS. Use specific origins in production (e.g., `https://yourdomain.com`). `allow_credentials=False` when wildcard per CORS spec.

## Database (6 tables + 1 column added)

- `users` - WhatsApp users
- `conversations` - Chat history with metadata (intent, verdict, confidence)
- `health_items` - Product KB with ingredients, structured flagged data, aliases, scores
- `user_products` - Products each user has checked (for footprint/progress/swap)
- `feedback` - User ratings (good/bad) with reasons
- `unknown_queries` - Products users asked about that aren't in KB

## Testing Notes

- Tests use env vars from `tests/conftest.py` (overrides `.env`)
- `conftest.py` clears `get_settings` LRU cache to ensure test env vars are used
- Mock fixtures: `mock_supabase`, `mock_http_client`, sample WhatsApp payloads
- All async tests use `@pytest.mark.asyncio` with strict mode

## Don't

- Don't use Unicode characters (arrows, em-dashes) in `.env` or `prompts/` - causes ASCII encoding errors with API clients
- Don't use `maybe_single()` on Supabase queries - crashes on empty results
- Don't put inline comments after values in `.env` - pydantic-settings doesn't strip them
- Don't store scores in the database - always compute on-the-fly from `flagged_ingredients`
- Don't route footprint/swap commands through AI - they're deterministic backend operations
- Don't commit `.env`, `test_conversations.txt`, or `venv/`
- Don't use `import` inside function bodies - move all imports to module top level (PEP 8)

## Workflow Orchestration

### 1. Plan Node Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately - don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes - don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests - then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.
