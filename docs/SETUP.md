# Setup & Deployment Guide

## Prerequisites

- Python 3.12+
- A Supabase account (free tier works)
- A Meta Developer account with WhatsApp Business API access
- A Google AI Studio account (for Gemini API key)
- ngrok (for local webhook testing)

---

## 1. Clone & Install

```bash
git clone <your-repo-url>
cd UnPlastic

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies (for testing)
pip install -r requirements-dev.txt
```

---

## 2. Supabase Setup

### Create Project
1. Go to [supabase.com](https://supabase.com) and sign up
2. Click **New Project**
3. Choose a name, set a database password, select a region
4. Wait for the project to initialize

### Get Credentials
1. Go to **Project Settings** (gear icon) > **API**
2. Copy:
   - **Project URL** --> `SUPABASE_URL`
   - **service_role key** (under "Project API keys") --> `SUPABASE_SERVICE_ROLE_KEY`

> Use the **service_role** key, NOT the anon key. The service_role key bypasses Row Level Security, which is required for server-side operations.

### Create Tables
1. Go to **SQL Editor** in the left sidebar
2. Click **New Query**
3. For a **fresh install**: paste the contents of `migrations/001_initial_schema.sql` and click **Run**
4. For an **existing install**: run these in order:
   - `002_upgrade_schema.sql` (ingredients, aliases, metadata)
   - `003_feedback.sql` (feedback table)
   - `004_user_products.sql` (user product history for footprint/progress)
   - `005_user_activity.sql` (last_active_at for 24h window tracking)
5. You should see "Success. No rows returned" for each

### Seed Product Data
```bash
python scripts/seed_health_items.py
```

This loads curated health products (with full ingredients, structured flagged data, and aliases) into the database. Use `--update` to refresh existing entries:
```bash
python scripts/seed_health_items.py --update
```

---

## 3. Google Gemini API Key

1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Sign in with your Google account
3. Click **Get API Key** > **Create API key**
4. Copy the key --> `GEMINI_API_KEY`

The free tier allows 15 requests per minute, which is plenty for development.

---

## 4. WhatsApp Business API Setup

### a) Create Meta Developer Account
1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Register as a developer (requires Facebook account)

> **Common issue:** If your Facebook account is new, Meta may block you with "Your Facebook account is too new to create a business account." Wait 1 hour and try again.

### b) Create App
1. Click **Create App** > select **Other** > **Business** type
2. Name it (e.g., "Veda Health Coach")
3. You'll be asked to connect a **Business Portfolio**:
   - Click **Create a new business portfolio**
   - Fill in a business name (your name or project name works)
   - Verification is NOT required for development - you can verify later for production
   - An unverified portfolio is fine for testing with up to 5 phone numbers

### c) Add WhatsApp
1. In your app dashboard, click **Add Product**
2. Find **WhatsApp** > click **Set Up**
3. This gives you a free **test phone number** (displays as "Test Number" - you cannot rename this)

### d) Get Credentials
Go to **WhatsApp** > **API Setup**:
- **Phone Number ID** (shown under the "From" phone number) --> `WHATSAPP_PHONE_NUMBER_ID`
- **Temporary Access Token** --> `WHATSAPP_ACCESS_TOKEN`

> **Important:** The temporary token **expires every 24 hours**. You'll need to get a new one daily during development. See "Permanent Access Token" section below for a non-expiring token.

### e) Set Your Verify Token
This is any random string YOU create - it's a shared secret between your server and Meta:
```bash
python -c "import secrets; print(secrets.token_urlsafe(16))"
```
Save this as `WHATSAPP_VERIFY_TOKEN` in your `.env`. You'll enter this same value in Meta's webhook configuration.

### f) Add Test Phone Numbers
1. On the API Setup page under **"To"**, click **Manage phone number list**
2. Add your personal WhatsApp number
3. You'll receive a verification code on WhatsApp - enter it
4. You can add up to 5 test numbers on the free tier

### g) Send Initial Template Message
Before you can have a two-way conversation, the business must initiate contact:
1. On the API Setup page, click **Send Message** (sends a "how_to_use" template to your number)
2. You'll receive this template message on your WhatsApp
3. **Reply to it** - this opens a 24-hour conversation window for free-form messaging

### h) Configure Webhook

> **Your server must be running before this step.** Start uvicorn + ngrok first.

1. Go to **WhatsApp** > **Configuration**
2. Click **Edit** on the Webhook section
3. Set:
   - **Callback URL**: `https://your-ngrok-url.ngrok-free.app/webhook/whatsapp`
   - **Verify Token**: same value as `WHATSAPP_VERIFY_TOKEN` in your `.env`
4. Click **Verify and Save**

> **Common issue:** "The callback URL or verify token couldn't be validated."
> - Make sure both uvicorn AND ngrok are running
> - Make sure the URL ends with `/webhook/whatsapp` (not just the base URL)
> - Check the verify token matches exactly - no extra spaces or quotes
> - Test ngrok is working by visiting `https://your-ngrok-url.ngrok-free.app/health` in your browser

### i) Subscribe to Webhook Fields

**This step is easy to miss but required!** Without it, Meta won't forward messages to your server.

1. On the same Configuration page, scroll to **Webhook fields**
2. Click **Manage**
3. Find `messages` and toggle **Subscribe** ON
4. Click **Done**

### j) Test It
1. Send a message from your WhatsApp to the test number: "Is Dove soap safe?"
2. You should see the POST request in your uvicorn terminal
3. A reply should arrive on your WhatsApp within a few seconds

> **About the test number:** The test number displays as "Test Number" in WhatsApp. You cannot change this name. To get a custom display name, you need to add your own phone number (see "Using Your Own Phone Number" below).

### Using Your Own Phone Number (Optional)
1. Go to **WhatsApp Manager** > **Phone Numbers** > **Add Phone Number**
2. Enter a phone number you own (must NOT already be registered on WhatsApp)
3. Verify via SMS or voice call
4. Set a **Display Name** (e.g., "Veda Health Coach") - this gets reviewed by Meta (1-3 days)

---

## 5. Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and fill in all values:

```bash
# WhatsApp
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxx
WHATSAPP_PHONE_NUMBER_ID=123456789
WHATSAPP_VERIFY_TOKEN=your-random-string

# Gemini
GEMINI_API_KEY=AIzaxxxxxxx
GEMINI_MODEL=gemini-2.5-flash
GEMINI_MAX_TOKENS=1024
GEMINI_TEMPERATURE=0.3

# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhxxxxxxx

# Admin
ADMIN_API_KEY=your-long-random-string

# Security (optional in dev, required in production)
WHATSAPP_APP_SECRET=your-app-secret

# CORS (optional, defaults to *)
CORS_ORIGINS=https://yourdomain.com,https://admin.yourdomain.com

# App
ENVIRONMENT=development
```

Generate a secure admin key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**`WHATSAPP_APP_SECRET`**: Found in Meta App Dashboard > Settings > Basic > App Secret. Used to verify `X-Hub-Signature-256` on incoming webhooks. Optional for development (signature check is skipped if empty), but should be set in production.

**`CORS_ORIGINS`**: Comma-separated list of allowed origins (e.g., `https://yourdomain.com`). Defaults to `*` (allow all). When using wildcard, `allow_credentials` is automatically set to `False` per CORS spec.

> Never put real credentials in `.env.example` - that file gets committed to Git.

---

## 6. Run Locally

### Start the server
```bash
uvicorn app.main:app --reload --port 8000
```

Verify it's running:
```bash
curl http://localhost:8000/health
# {"status":"ok","checks":{"server":"ok","database":"ok"}}
```

The health check now verifies Supabase connectivity. If the database is unreachable, it returns `{"status":"degraded","checks":{"server":"ok","database":"error"}}`.

Swagger docs available at: http://localhost:8000/docs

### Expose via ngrok
In a second terminal:
```bash
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok-free.app`).

### Configure WhatsApp Webhook
If you haven't already, follow steps 4h and 4i above to configure the webhook with your ngrok URL.

### Test
1. Send the initial template message from Meta API Setup page (step 4g)
2. Reply from your WhatsApp with: "Is Dove soap safe?"
3. You should receive a health analysis reply within a few seconds

---

## 7. Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_response_formatter.py -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=term-missing
```

---

## 8. Docker (Local Development)

### Using Docker Compose
```bash
docker-compose up --build
```

This starts the server on port 8000 with hot-reload enabled.

### Using Dockerfile directly
```bash
docker build -t veda-health-coach .
docker run -p 8000:8000 --env-file .env veda-health-coach
```

---

## 9. Production Deployment (Railway)

1. Push code to GitHub
2. Go to [railway.app](https://railway.app) > **New Project** > **Deploy from GitHub**
3. Select your repository
4. Add all environment variables from `.env` (Settings > Variables)
5. Set `ENVIRONMENT=production`
6. Railway auto-detects the Dockerfile and deploys
7. Get your production URL from Railway dashboard

### Update Webhook URLs
- **WhatsApp**: Update Callback URL in Meta Dashboard to your Railway domain
- Set `WHATSAPP_VERIFY_TOKEN` to the same value

### Permanent WhatsApp Access Token
For production, create a permanent token (the temporary one expires daily):
1. Go to [business.facebook.com/settings](https://business.facebook.com/settings)
2. **Users** > **System Users** > **Add**
3. Name: "Veda Bot", Role: Admin
4. **Add Assets** > select your WhatsApp app > Full Control
5. **Generate New Token** > add permissions: `whatsapp_business_messaging`, `whatsapp_business_management`
6. Copy the token > update `WHATSAPP_ACCESS_TOKEN`

---

## 10. Adding Products to Knowledge Base

### Via Admin API
```bash
curl -X POST http://localhost:8000/admin/health-items \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-admin-key" \
  -d '{
    "item_name": "CeraVe Moisturizing Cream",
    "brand": "CeraVe",
    "category": "personal_care",
    "flagged_ingredients": [],
    "risk_level": "low",
    "recommendation": "Great for sensitive skin",
    "notes": "Fragrance-free, dermatologist recommended"
  }'
```

### Via Seed Script
1. Add entries to `scripts/seed_data_v2.json` (structured format with ingredients, flagged data, aliases)
2. Run `python scripts/seed_health_items.py` (or `--update` to refresh existing)

### Check Unknown Queries
See what users are asking about that isn't in your database:
```bash
curl -H "X-API-Key: your-admin-key" http://localhost:8000/admin/unknown-queries
```

### Review User Feedback
See what users rated as helpful or not helpful:
```bash
# All feedback
curl -H "X-API-Key: your-admin-key" http://localhost:8000/admin/feedback

# Only bad feedback (most useful for improvement)
curl -H "X-API-Key: your-admin-key" "http://localhost:8000/admin/feedback?rating=bad"
```

### View Analytics Dashboard
Get a complete overview of bot performance:
```bash
curl -H "X-API-Key: your-admin-key" http://localhost:8000/admin/analytics
```

Returns: total users, messages, KB match rate, satisfaction rate, top unresolved queries, and bad feedback reasons.

Use unknown queries to prioritize which products to add next. Use bad feedback to identify where the AI fails and refine the prompt. Use analytics to track overall quality over time.

---

## Troubleshooting

### WhatsApp Setup Issues

| Issue | Solution |
|---|---|
| "Your Facebook account is too new" | Wait 1 hour and try again. Meta rate-limits new accounts from creating business portfolios. |
| "Callback URL couldn't be validated" | Most common cause: your Callback URL is missing `/webhook/whatsapp` at the end. Must be `https://xxx.ngrok-free.app/webhook/whatsapp`, not just the base URL. Also ensure server + ngrok are both running. |
| No reply after sending WhatsApp message | You forgot to subscribe to the `messages` webhook field. Go to WhatsApp > Configuration > Webhook fields > Manage > toggle `messages` ON. |
| "Session has expired" / 401 errors | Your temporary access token expired (happens every 24 hours). Get a new one from WhatsApp > API Setup, or create a permanent System User token. |
| Can't generate permanent token ("No permissions available") | You need to assign your WhatsApp app to the System User first. Go to the System User > Add Assets > Apps > select your app > Full Control > Save. Then try generating the token again. |
| Test number shows "Test Number" | This is the free sandbox number - you cannot rename it. Add your own phone number for a custom display name. |
| ngrok URL changed | Free ngrok gives a new URL each restart. Update the Callback URL in Meta webhook configuration every time. |

### Server & Database Issues

| Issue | Solution |
|---|---|
| `table not found` error | Run `migrations/001_initial_schema.sql` in Supabase SQL Editor. For upgrades, also run 002 and 003. |
| `maybe_single` / `Missing response` error | Known supabase-py issue. The code uses `.limit(1)` to work around it. If you see this, check you're on the latest code. |
| `ascii codec can't encode` error | Your `.env` file or prompt file contains Unicode characters (arrows, em-dashes). Remove any non-ASCII characters from `.env` values. Never put comments with special characters on the same line as env values. |
| `.env` values not loading correctly | In `.env` files, everything after `=` is the value - `#` comments on the same line are NOT stripped. Put values alone: `KEY=value` with no inline comments. |
| Gemini returns plain text instead of JSON | The `response_schema` in `ai_engine.py` enforces JSON at the API level. Restart the server to pick up code changes. |
| Gemini model not found (404) | The model name may have changed. Check [Google AI docs](https://ai.google.dev/models) for current model names. Update `GEMINI_MODEL` in `.env`. |
| Duplicate messages in WhatsApp | Normal - Meta retries webhooks. The idempotency check on `whatsapp_msg_id` prevents double processing. |
| Seed script fails with "NoneType" errors | The seed script had a `maybe_single()` bug. Make sure you're using the latest version that uses `.limit(1)` instead. |
