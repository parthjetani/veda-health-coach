# Veda - AI Health Coaching Chatbot

A production-grade WhatsApp AI health coach powered by Google Gemini, Supabase, and FastAPI. Veda checks products, tracks your chemical exposure, and helps you make smarter health choices over time.

**Not just a chatbot - a personal health tracking system.**

## Tech Stack

| Component | Technology |
|---|---|
| Backend | Python 3.12 + FastAPI |
| AI Engine | Google Gemini 2.5 Flash (text + vision) |
| Database | Supabase (PostgreSQL + pg_trgm) |
| Messaging | WhatsApp Cloud API (Meta Graph API) |
| Deployment | Docker + Railway/Render |

## Features

**Product Analysis**
- Product Verdict Score (0-100) - deterministic, shareable, comparable
- Product label photo analysis (Gemini Vision)
- Product Comparison Mode ("Compare Dove vs Pears" - side-by-side with scores)
- Before/After swap comparison with score delta
- EWG safety database ratings (when available)
- Curated knowledge base (65+ Indian products) with full ingredients and aliases

**Personal Health Tracking**
- Personal Chemical Footprint - tracks all products you've checked
- Smart Swap Priority - which product to replace first for biggest improvement
- Progress Feedback - score trend, milestone messages, high-risk reduction tracking
- Auto-nudge after 3 products ("Type 'my footprint' to see your summary")

**Growth & Retention**
- User-Powered Database - auto-captures products from AI analysis into KB
- Daily Health Tips - 30 curated tips with admin trigger endpoint
- Interactive feedback buttons (Helpful / Not helpful) after every reply
- Share prompt for organic viral growth

**Production Hardening**
- Gemini timeout (8 sec) + retry once with fallback health tips
- Per-user rate limiting (30 messages/hour via DB count)
- Large image rejection (>5MB)
- Contextual error messages (5 custom exception types)
- 24h WhatsApp window handling with template message fallback
- Conditional test logging (dev only, disabled in production)

## Special Commands

Users can type these on WhatsApp:
- **"my footprint"** / **"my products"** - see chemical exposure summary
- **"what should I swap"** / **"swap priority"** - personalized swap recommendations
- **"Compare Dove vs Pears"** - side-by-side product comparison with scores

## Project Structure

```
app/
|-- api/
|   |-- webhooks/              # WhatsApp webhook (messages + feedback buttons)
|   |-- admin/                 # CRUD + footprint + feedback + analytics
|-- core/
|   |-- message_handler.py     # Central orchestrator + command routing
|   |-- product_scorer.py      # Verdict Score (0-100) algorithm
|   |-- footprint.py           # Chemical footprint analysis + progress
|   |-- swap_priority.py       # Smart swap ranking
|   |-- product_comparison.py  # Side-by-side product comparison
|   |-- daily_tips.py          # 30 health tips + send function
|   |-- feedback_handler.py    # Feedback button processing
|   |-- response_formatter.py  # JSON -> WhatsApp text + score + progress
|   |-- errors.py              # Custom exceptions (5 types)
|   |-- security.py            # Admin API key auth
|-- services/
|   |-- ai_engine.py           # Google Gemini API (text + vision + structured JSON)
|   |-- whatsapp_client.py     # Send messages, media download, feedback buttons
|   |-- knowledge_base.py      # Product search, context, swap comparison
|   |-- source_context.py      # Ingredient source citations (NIH, FDA, EWG)
|   |-- conversation.py        # Chat history with metadata
|-- db/queries/                # Supabase query layer
|-- models/                    # Pydantic validation
|-- config.py                  # Environment settings
|-- main.py                    # FastAPI app factory
```

## Quick Start

See [docs/SETUP.md](docs/SETUP.md) for the full setup guide.

```bash
# Install
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp .env.example .env   # Fill in your API keys

# Database (run all migrations in Supabase SQL Editor)
# migrations/001_initial_schema.sql
# migrations/002_upgrade_schema.sql
# migrations/003_feedback.sql
# migrations/004_user_products.sql

# Seed product data
python scripts/seed_health_items.py

# Run
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/webhook/whatsapp` | WhatsApp webhook verification |
| POST | `/webhook/whatsapp` | Receive messages + feedback + special commands |
| GET | `/admin/users` | List all users (paginated) |
| GET | `/admin/health-items` | List KB with scores (filterable) |
| POST | `/admin/health-items` | Add product to KB |
| PUT | `/admin/health-items/{id}` | Update product |
| DELETE | `/admin/health-items/{id}` | Delete product |
| GET | `/admin/unknown-queries` | Unmatched user queries |
| GET | `/admin/feedback` | User feedback (filterable by rating) |
| GET | `/admin/user-footprint/{id}` | User's chemical footprint |
| GET | `/admin/analytics` | Dashboard metrics |
| POST | `/admin/send-daily-tip` | Send health tip to all active users |

Admin endpoints require `X-API-Key` header. Swagger docs at `/docs` in development.

## Database Migrations

```
migrations/
|-- 001_initial_schema.sql      # Full schema (fresh install)
|-- 002_upgrade_schema.sql      # Add ingredients, aliases, structured flags, metadata
|-- 003_feedback.sql            # Feedback table
|-- 004_user_products.sql       # User product history (footprint, progress, swap priority)
|-- 005_user_activity.sql       # last_active_at for 24h window tracking
```

## Documentation

- [API Reference](docs/API.md)
- [Architecture Overview](docs/ARCHITECTURE.md)
- [Setup & Deployment Guide](docs/SETUP.md)

## Architecture

```
WhatsApp User
     | sends message, photo, or taps button
     v
Meta Cloud API
     | POST /webhook/whatsapp
     v
FastAPI (returns 200 immediately)
     | BackgroundTask
     v
Command Router
     |-- "my footprint" -> footprint.py (bypass AI)
     |-- "what should I swap" -> swap_priority.py (bypass AI)
     |-- "compare X vs Y" -> product_comparison.py (bypass AI)
     |-- product query -> AI pipeline:
           |-- KB lookup (fuzzy + alias + substring)
           |-- Calculate Product Score (0-100)
           |-- Build product + source + swap context
           |-- Auto-save to user_products
           |-- Call Gemini API
           |-- Format response + score + progress
           |-- Send reply + feedback buttons
```
