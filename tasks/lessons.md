# Lessons Learned

Patterns and mistakes to avoid. Review at session start.

## Supabase
- Never use `maybe_single()` - crashes on empty results. Use `.limit(1)` instead.
- Use `service_role` key, NOT `anon` key for server-side operations.

## Environment
- Never put inline comments after values in `.env` - pydantic-settings treats everything after `=` as the value.
- Never use Unicode characters (arrows, em-dashes) in `.env` or prompt files - causes ASCII encoding errors with API clients.
- `extra="ignore"` in Settings prevents crashes from leftover env vars.

## WhatsApp
- Always return 200 immediately from webhook - Meta retries on non-200 and can disable your webhook permanently.
- Temporary access token expires every 24h - use System User permanent token for production.
- Callback URL must include `/webhook/whatsapp` path - not just the base domain.
- Must subscribe to `messages` webhook field - without it, no messages are forwarded.

## AI/Gemini
- Prompt-only JSON enforcement is unreliable - use `response_schema` at API level.
- `temperature=0.3` for consistent, low-hallucination health responses.
- Score is deterministic (Python) - never let the AI calculate or override scores.
- Special commands (footprint, swap) bypass AI entirely - faster and cheaper.

## Testing
- Clear `get_settings.cache_clear()` in conftest.py so test env vars override real `.env`.
- Use `os.environ["KEY"] = "value"` (force set), not `setdefault` (won't override existing).

## Code Style
- Never use `import` inside function bodies. Move all imports to module top level (PEP 8). Imports inside functions are a code smell - they hide dependencies, make the module harder to understand, and can mask circular import issues that should be resolved properly.

## CORS
- Never use `allow_credentials=True` with a wildcard (`*`) origin. The CORS spec forbids it and browsers will reject the response. Use specific origins when credentials are needed.

## Conversation History
- Never store formatted WhatsApp text (with emoji, score lines, share prompts) in conversation history. It pollutes the context window when injected into subsequent AI calls. Store the clean AI summary and keep the raw JSON in metadata for debugging.

## Architecture
- Plan before building any non-trivial feature.
- Verify implementation against the plan before marking done.
- Use /content-research-writer skill for any feature implementation or codebase changes.

## Data Integrity
- Never use placeholder text ("product label image") for DB writes. Extract real names from AI responses.
- Inferred product guardrails: name >= 5 chars, >= 2 words, non-empty ingredients, blocklist, fuzzy dedup.
- Always use the SAME cleaned name for both user_products and health_items (consistency across storage layers).

## Testing
- Unit tests are not enough. Build conversation simulators that test the full pipeline end-to-end.
- Mock only external APIs (Gemini, WhatsApp, Supabase). Test all internal logic with real code paths.
- Fixture functions for pytest should be sync unless they need async setup. Async fixtures cause "can't send non-None value" errors.

## Product Thinking
- More features than users is a product smell. Ship and get feedback before building more.
- Stop asking "what can I add?" and start asking "where does it feel wrong to the user?"
- ChatGPT gives good high-level advice but doesn't know what's already implemented. Always verify before acting on suggestions.
