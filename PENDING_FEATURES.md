# Veda - Pending Features & Future Roadmap

What remains to be done. For completed features, see README.md and docs/ARCHITECTURE.md.

---

## P0 - Must Do (before sharing with real users)

#### 1. Deploy to Production
**Why:** Currently runs locally with ngrok. Needs 24/7 hosting for real users.

**What to do:**
- Push to GitHub (private repo)
- Deploy to Railway or Render
- Set all env vars in deployment platform
- Update Meta webhook URL to production domain

---

## P1 - Should Do (after first 50 users)

#### 4. Add Billing (Razorpay)
**Why:** Monetization when ready.

**What to build:**
- `app/services/razorpay_service.py` - webhook signature verification + event handling
- `app/api/webhooks/razorpay.py` - POST endpoint for Razorpay events
- Re-enable subscription gate in `message_handler.py`
- Handle events: `subscription.activated`, `subscription.cancelled`, `payment.captured`

**Architecture already supports this:**
- `users.is_active` column exists
- `users.stripe_customer_id` column exists (rename to `payment_customer_id`)
- Gate check code was previously written and removed - can be restored

#### 5. Facebook Messenger Integration
**Why:** Expands reach. Original requirement.

**What to build:**
- `app/api/webhooks/messenger.py` - webhook for Messenger
- `app/services/messenger_client.py` - send messages via Messenger API
- `app/models/messenger.py` - Pydantic models for Messenger webhook
- Add `messenger_user_id` and `preferred_channel` columns to users table
- See `MIGRATION_GUIDE.md` for full implementation details

#### 6. Barcode Scanning
**Why:** Users can scan a barcode instead of typing product name.

**What to build:**
- User sends a photo of a barcode
- Use Gemini Vision to read the barcode number
- Look up barcode in health_items table (column already exists)
- If not found, try Open Food Facts API for product data

**Schema ready:** `health_items.barcode` column exists

---

## P2 - Nice to Have (after product-market fit)

#### 7. Multi-Language Support
**Why:** India has many languages.

**What to build:**
- Detect user's language from message
- Prompt already says "respond in user's language" but product data is English-only
- Consider translating product names and common responses
- Hindi is the highest-priority addition

#### 8. Web Dashboard (Admin)
**Why:** Current admin is API-only. A web dashboard would be easier for non-technical users.

**What to build:**
- Simple React/Next.js frontend connecting to existing admin API
- Shows: analytics dashboard, product management, feedback review, unknown queries
- See `ADMIN_UI_PLAN.md` for full design

#### 9. Daily Tips Automation
**Why:** The daily tip function and 30 tips are built. Need cron automation.

**What to do:**
- Set up Railway cron job to call `POST /admin/send-daily-tip` daily
- Get Meta-approved template message for daily tips

#### 10. Add EWG Ratings to Products (Manual Data Entry)
**Why:** Code is built to show EWG ratings. Need to manually add data.

**What to do:**
- Look up top 20-30 international brand products on [ewg.org/skindeep](https://www.ewg.org/skindeep/)
- Add `ewg_rating` values to seed data files
- Run `python scripts/seed_health_items.py --update`
- ~30 minutes of manual work

---

## Pre-Launch Checklist (Actions Only - Code is Done)

| # | Item | Status |
|---|---|---|
| 1 | Push code to GitHub (private repo) | NOT DONE |
| 2 | Deploy to Railway or Render | NOT DONE |
| 3 | Update Meta webhook URL to production domain | NOT DONE |
| 4 | Test with 5 real people | NOT DONE |

## Monitoring (set up after deploy)

| # | Item | Why |
|---|---|---|
| 8 | Server health monitoring | Railway/Render have built-in alerts. Set up uptime ping. |
| 9 | Check Supabase dashboard weekly | Free tier: 500MB DB, 2GB bandwidth. |
| 10 | Check Gemini usage weekly | Free tier: 1500 requests/day. |
| 11 | Review `/admin/analytics` regularly | KB match rate, satisfaction, top unknown queries. |
| 12 | Conversation cleanup (after 30 days) | Delete old message_text to save DB space. |

---

## Technical Debt

| Item | Priority |
|---|---|
| Push to GitHub | High |

---

## Environment & Accounts Needed

| Service | Status |
|---|---|
| Supabase | Active (free tier) |
| Google Gemini | Active (free tier) |
| Meta Developer | Active (webhook configured) |
| Meta Business | Pending verification |
| WhatsApp Token | Temporary (need permanent) |
| Railway/Render | Not created |
| GitHub | Not created |
| Razorpay | Not created (future billing) |
