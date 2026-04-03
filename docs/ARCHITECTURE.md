# Architecture Overview

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Web Framework | FastAPI (Python 3.12) | Async API server with auto-generated docs |
| AI Engine | Google Gemini 2.5 Flash | Text + vision analysis, structured JSON output |
| Database | Supabase (PostgreSQL) | Users, conversations, product KB, feedback |
| Messaging | WhatsApp Cloud API (Meta) | Messages, media, interactive buttons |
| Search | PostgreSQL pg_trgm | Fuzzy + substring + alias matching |

---

## System Architecture

```
WhatsApp User
     |
     | sends message (text, photo, or button tap)
     v
Meta Cloud API
     |
     | POST /webhook/whatsapp
     v
FastAPI Server (returns 200 immediately)
     |
     | BackgroundTask
     v
+----------------------------------------------------+
| message_handler.py (messages)                      |
| feedback_handler.py (button taps)                  |
+----------------------------------------------------+
     |
     |-- 1. Idempotency check (skip duplicate webhooks)
     |-- 2. Get or create user (Supabase)
     |-- 3. Download image if present (WhatsApp CDN)
     |-- 4. Fetch conversation history (last 10 messages)
     |-- 5. Knowledge base lookup (fuzzy + alias + substring)
     |       |
     |       |-- Match found --> build product + source context
     |       |-- Affirmation ("yes") --> build alternatives context
     |       |-- No match --> log to unknown_queries
     |
     |-- 6. Store user message
     |-- 7. Call Gemini API (structured JSON schema enforced)
     |-- 8. Parse JSON + confidence-based tone alignment
     |-- 9. Extract metadata (intent, verdict, confidence)
     |-- 10. Store assistant reply with metadata
     |-- 11. Send reply via WhatsApp API
     |-- 12. Send feedback buttons (Helpful / Not helpful)
     v
WhatsApp User receives reply + feedback buttons
```

---

## Project Structure

```
app/
|-- api/
|   |-- webhooks/
|   |   |-- whatsapp.py      # Messages + interactive button replies
|   |-- admin/
|       |-- users.py          # GET /admin/users
|       |-- health_items.py   # CRUD + unknown queries + feedback + analytics
|
|-- core/
|   |-- message_handler.py    # Central orchestrator + command routing
|   |-- product_scorer.py     # Verdict Score (0-100) deterministic algorithm
|   |-- footprint.py          # Chemical footprint analysis + progress tracking
|   |-- swap_priority.py      # Smart swap ranking by impact
|   |-- product_comparison.py # Side-by-side product comparison
|   |-- daily_tips.py         # 30 health tips + send function
|   |-- feedback_handler.py   # Feedback button processing
|   |-- response_formatter.py # JSON -> WhatsApp text + score + progress
|   |-- errors.py             # Custom exceptions (5 types)
|   |-- security.py           # API key validation
|
|-- services/
|   |-- ai_engine.py          # Gemini API (text + vision + timeout + retry)
|   |-- whatsapp_client.py    # Send messages, templates, media, feedback buttons
|   |-- knowledge_base.py     # Product search, context, swap comparison, alternatives
|   |-- source_context.py     # Ingredient citations (NIH, FDA, EWG)
|   |-- conversation.py       # Chat history with metadata
|
|-- db/queries/
|   |-- users.py              # User CRUD
|   |-- conversations.py      # Message CRUD + metadata
|   |-- health_items.py       # Product CRUD + fuzzy search
|   |-- user_products.py      # User product history (upsert, list, count)
|   |-- unknown_queries.py    # Curation queue
|   |-- feedback.py           # Feedback storage + retrieval
|   |-- analytics.py          # Dashboard metrics
|
|-- models/
|   |-- whatsapp.py           # Webhook payloads (text, image, interactive)
|   |-- ai_response.py    # AI structured response schema (AIResponse)
|   |-- admin.py              # Admin models (FlaggedIngredient, HealthItem)
|
|-- config.py                  # All environment settings
|-- main.py                    # App factory + lifespan
```

---

## Database Schema

### Tables

**users** - WhatsApp users
- `whatsapp_number` (unique, E.164 format)
- `is_active` (default: true)
- Auto-managed `created_at`, `updated_at`

**conversations** - Chat history with analytics
- `user_id` (FK to users)
- `role` (user or assistant)
- `message_text`
- `whatsapp_msg_id` (unique - idempotency)
- `metadata` (jsonb - intent, verdict, confidence, kb_match)
- Indexed by `(user_id, timestamp DESC)`

**health_items** - Product knowledge base
- `item_name`, `brand`, `category`
- `ingredients` (jsonb - full ingredient list from label)
- `flagged_ingredients` (jsonb - structured: `[{name, reason, risk}]`)
- `risk_level` (high/medium/low)
- `recommendation`, `alternative_brand`
- `aliases` (text[] - search synonyms like "dove soap", "dove bar")
- `confidence_source` (verified/inferred/community)
- Trigram indexes on `item_name`, `brand` + GIN index on `aliases`

**unknown_queries** - Curation queue
- `query_text`, `user_id`
- `resolved` (boolean - set true when product added to KB)
- `resolved_item_id` (FK to health_items)

**feedback** - User ratings on AI responses
- `rating` (good/bad)
- `reason` (incorrect/generic/other - only for bad ratings)
- `user_query`, `ai_response` - the original Q&A that was rated
- `message_id` - WhatsApp message ID

**user_products** - Products each user has checked (foundation for footprint/swap/progress)
- `user_id` (FK to users)
- `health_item_id` (FK to health_items, nullable for inferred products)
- `product_name`, `score`
- `confidence_source` (verified = KB match, inferred = AI analysis)
- `check_count` (incremented on re-check), `still_using`
- `first_checked_at`, `last_checked_at`
- Unique on `(user_id, product_name)`

### Search Function

`search_health_items(query, threshold)` uses three matching strategies:
1. **Trigram similarity** on `item_name` and `brand` (fuzzy matching)
2. **Substring ILIKE** (catches exact matches within sentences)
3. **Alias matching** (user types "dove soap", matches "Dove Beauty Bar")

Returns top 5 results sorted by similarity score.

### Migrations

```
migrations/
|-- 001_initial_schema.sql      # Full schema for fresh installs
|-- 002_upgrade_schema.sql      # Add ingredients, aliases, structured flags, metadata
|-- 003_feedback.sql            # Feedback table
|-- 004_user_products.sql       # User product history (footprint, progress, swap priority)
|-- 005_user_activity.sql       # last_active_at for 24h window tracking
```

---

## Key Design Decisions

### 1. Always return 200 to Meta
Meta retries on non-200. Server returns 200 immediately, processes in `BackgroundTasks`.

### 2. Idempotency via whatsapp_msg_id
Unique constraint on `whatsapp_msg_id` prevents duplicate message processing.

### 3. Structured JSON output (API-level enforcement)
Gemini's `response_mime_type="application/json"` + `response_schema` forces exact JSON structure. More reliable than prompt-only enforcement.

### 4. Knowledge base context injection
Product data injected as `<product_context>` XML block in system prompt. AI gets verified data instead of guessing.

### 5. Conversation history (10 messages)
Last 10 messages sent to Gemini. Balances context quality vs token cost/speed.

### 6. Affirmation detection for recommendations
"yes", "sure", "tell me" -> scans history for last product check -> fetches low-risk alternatives from same category -> injects as context.

### 7. Confidence-based tone alignment
- **high** -> strong, confident response
- **medium** -> soft nudge to send ingredient list
- **low** -> honest uncertainty, asks for more data

### 8. Feedback loop
Interactive WhatsApp buttons after every reply. Bad ratings trigger follow-up (Incorrect/Generic/Other). All stored for iteration.

### 9. Structured flagged ingredients
`[{name, reason, risk}]` instead of flat `["Fragrance"]`. Pre-written reasons reduce AI hallucination and improve consistency.

### 10. Full ingredient list storage
Products store the complete label ingredients. Passed to AI for accurate analysis instead of relying on training knowledge.

### 11. Before/After swap comparison
When a product has an `alternative_brand` and that alternative exists in the DB with a lower risk level, the system automatically injects a SWAP COMPARISON block into the product context. This enables Gemini to present a clear "switch from X to Y" recommendation with specific data.

### 12. Share prompt for organic growth
Product check responses with high or medium confidence append a share nudge: "Know someone who uses this product? Forward this to them!" — leveraging WhatsApp's forward culture for organic growth.

### 13. Analytics dashboard
`GET /admin/analytics` aggregates key metrics from conversations, feedback, and unknown queries in a single call. Shows KB match rate, satisfaction rate, and top unresolved queries.

### 14. Product Verdict Score (0-100)
Deterministic scoring algorithm in `product_scorer.py`. Deducts points per flagged ingredient by risk level (high: -30, medium: -15, low: -5). Score is consistent everywhere (WhatsApp, API, swap comparisons). Computed on-the-fly, never stored in health_items.

### 15. Personal Chemical Footprint
`user_products` table tracks every product a user checks. `footprint.py` aggregates: average score, top chemical exposures, highest risk product, best swap, score trend. Bypasses AI entirely — pure backend computation. Triggered by "my footprint" command.

### 16. Smart Swap Priority
`swap_priority.py` ranks user's products by swap impact (alt_score - current_score). Shows top 3 swaps with score deltas and removed ingredients. Bypasses AI. Triggered by "what should I swap" command.

### 17. Progress Feedback
Tracks score improvement over time. Shows delta, high-risk reduction count, milestone messages. Auto-nudge at 3 products to discover the footprint command. Creates the dopamine loop that drives retention.

### 18. Command routing (bypass AI for system features)
Special commands (footprint, swap, compare) are detected BEFORE the AI pipeline and handled by deterministic backend logic. Faster, cheaper, and more predictable than routing through the LLM.

### 19. Product Comparison Mode
"Compare X vs Y" looks up both products in KB, calculates scores, shows side-by-side comparison with winner. Entirely deterministic — no AI call needed.

### 20. User-Powered Database
When AI analyzes an unknown product, the result is auto-saved to `health_items` with `confidence_source='inferred'`. Guardrails prevent noisy data: skip if name < 3 chars, no verdict, or fuzzy match > 0.5 exists. DB grows automatically with every user interaction.

### 21. Production hardening
Gemini timeout (8 sec) + retry, per-user rate limiting (30/hour via DB count), large image rejection (>5MB), 5 custom exception types for contextual errors, 24h WhatsApp window fallback to template messages, 10 fallback health tips when AI is down, conditional test logging (dev only).

### 22. Webhook signature verification
Incoming WhatsApp webhooks are verified via `X-Hub-Signature-256` header using HMAC-SHA256 with `WHATSAPP_APP_SECRET`. This prevents forged webhook payloads. Optional in development (skipped if `WHATSAPP_APP_SECRET` is empty), but should always be set in production.

### 23. Conversation history stores clean summaries
Assistant messages stored in the `conversations` table use the AI summary text (from `ai_response.summary`), not the formatted WhatsApp reply (which includes emoji, score lines, share prompts). This keeps conversation history clean for context injection into subsequent Gemini calls. The full raw JSON response is preserved in the `metadata` column for debugging.

### 24. Prompt trimming (4500 to 1000 tokens)
System prompt (`prompts/health_coach.txt`) was reduced from 297 lines (~4500 tokens) to 93 lines (~1000 tokens). Sections redundant with `response_schema` enforcement were removed. Smaller prompts mean faster Gemini responses, lower cost, and more room for conversation context within the token budget.

### 25. EWG credibility layer
Products with `ewg_rating` show human-readable safety database rating ("Low concern (3/10)"). Used as supporting signal, never override for ingredient analysis. Prompt instructs AI to reference it softly.

### 26. Daily health tips
30 curated tips rotating daily. Admin endpoint `POST /admin/send-daily-tip` triggers sending to all active users via template message. Ready for cron automation.

---

## Data Flow: Product Check

```
User: "Is Dove soap safe?"
                |
                v
        search_health_items("Is Dove soap safe?")
        (fuzzy match on name + substring match + alias check)
                |
                v
        Matches "Dove Beauty Bar" via alias "dove soap" (score: 0.85)
                |
                v
        Build product context:
        "Product: Dove Beauty Bar
         Brand: Dove
         Risk Level: medium
         Full Ingredients: Sodium Lauroyl Isethionate, ...Fragrance, BHT...
         Flagged: Fragrance - undisclosed chemicals (medium); BHT - preservative (low)
         Alternative: Dr. Bronner's Unscented"
                |
                v
        Build source context:
        "Fragrance - EWG - undisclosed chemical mixtures"
                |
                v
        Calculate Product Score: 80/100 (Good)
        Build score breakdown: -15 Fragrance, -5 BHT
                |
                v
        Build swap comparison (with scores):
        "CURRENT: Dove Beauty Bar (Score: 80/100)
         SWAP TO: Dr. Bronner's (Score: 100/100)
         Improvement: +20 points"
                |
                v
        Auto-save to user_products table
                |
                v
        Calculate progress (if 2+ products):
        "Your average went from 65 to 72 (+7)"
                |
                v
        Gemini API (structured JSON schema enforced)
                |
                v
        Response formatter: score + verdict + progress + share prompt
                |
                v
        WhatsApp reply + feedback buttons
```

---

## Data Flow: Feedback

```
User taps "Not helpful"
        |
        v
    feedback_handler.py
        |-- Get last Q&A from conversation history
        |-- Store feedback (rating=bad, user_query, ai_response)
        |-- Send follow-up: "What felt off?"
        |       |-- "Incorrect"
        |       |-- "Too generic"
        |       |-- "Other"
        v
    User taps reason
        |
        v
    Update feedback record with reason
    Send: "Got it, thanks for the feedback!"
```

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Webhook parse failure | Return 200, log error |
| Duplicate message | Skip silently (idempotency) |
| Media download failure | Continue without image, log error |
| AI API failure | Send "Something went wrong" to user |
| DB query failure | Error handler sends fallback message |
| WhatsApp send failure | Retry 3 times, then log |
| Invalid AI JSON | Fallback: strip markdown, send raw text |
| Feedback button failure | Log error, don't block main flow |
