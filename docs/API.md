# API Reference

Base URL: `http://localhost:8000` (development) or your production domain.

Swagger UI available at `/docs` in development mode.

---

## Health Check

### GET /health

Returns application status.

**Response:**
```json
{
  "status": "ok",
  "checks": {
    "server": "ok",
    "database": "ok"
  }
}
```

When the database is unreachable:
```json
{
  "status": "degraded",
  "checks": {
    "server": "ok",
    "database": "error"
  }
}
```

---

## WhatsApp Webhook

### GET /webhook/whatsapp

Meta calls this endpoint to verify your webhook subscription.

| Query Parameter | Type | Description |
|---|---|---|
| hub.mode | string | Must be `subscribe` |
| hub.challenge | string | Challenge token to echo back |
| hub.verify_token | string | Must match `WHATSAPP_VERIFY_TOKEN` in .env |

**Success (200):** Returns `hub.challenge` as plain text.
**Failure (403):** Token mismatch.

---

### POST /webhook/whatsapp

Receives incoming WhatsApp messages and interactive button replies.

**Always returns 200 immediately.** Processing happens in a background task.

**Supported message types:**
- `text` - Regular text messages, special commands (footprint, swap, compare)
- `image` - Photos (product labels, ingredient lists). Rejected if >5MB.
- `interactive` - Button replies (feedback: Helpful / Not helpful)

**Special commands** (bypass AI, handled by backend):
- "my footprint" / "my products" -> chemical exposure summary
- "what should I swap" / "swap priority" -> personalized swap recommendations
- "compare X vs Y" / "X versus Y" -> side-by-side product comparison

**Rate limiting:** 30 messages per user per hour. Exceeding returns friendly message.

**Status updates** (delivery receipts) are detected and ignored.

**Response:**
```json
{"status": "ok"}
```

---

## Admin Endpoints

All admin endpoints require the `X-API-Key` header matching your `ADMIN_API_KEY` env var.

```bash
curl -H "X-API-Key: your-admin-key" http://localhost:8000/admin/users
```

**Error responses:**
- `422` - Missing X-API-Key header
- `403` - Invalid API key

---

### GET /admin/users

List all registered WhatsApp users.

| Query Parameter | Type | Default | Description |
|---|---|---|---|
| page | int | 1 | Page number (min: 1) |
| per_page | int | 20 | Items per page (min: 1, max: 100) |

**Response:**
```json
{
  "data": [
    {
      "id": "uuid",
      "whatsapp_number": "+919876543210",
      "is_active": true,
      "created_at": "2026-03-27T10:00:00Z",
      "updated_at": "2026-03-27T10:00:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "per_page": 20,
  "pages": 3
}
```

---

### GET /admin/health-items

List products in the knowledge base.

| Query Parameter | Type | Default | Description |
|---|---|---|---|
| page | int | 1 | Page number |
| per_page | int | 20 | Items per page (max: 100) |
| category | string | null | Filter: `food`, `supplement`, `personal_care`, `household`, `other` |
| risk_level | string | null | Filter: `high`, `medium`, `low` |

**Response:**
```json
{
  "data": [
    {
      "id": "uuid",
      "item_name": "Dove Beauty Bar",
      "brand": "Dove",
      "category": "personal_care",
      "ingredients": ["Sodium Lauroyl Isethionate", "Stearic Acid", "Fragrance", "BHT"],
      "flagged_ingredients": [
        {"name": "Fragrance", "reason": "undisclosed chemical mixture", "risk": "medium"},
        {"name": "BHT", "reason": "synthetic preservative", "risk": "low"}
      ],
      "risk_level": "medium",
      "recommendation": "Switch to a fragrance-free soap bar",
      "alternative_brand": "Dr. Bronner's Unscented",
      "aliases": ["dove soap", "dove bar", "dove beauty soap"],
      "confidence_source": "verified",
      "notes": "Fragrance is a catch-all for dozens of undisclosed chemicals"
    }
  ],
  "total": 32,
  "page": 1,
  "per_page": 20,
  "pages": 2
}
```

---

### POST /admin/health-items

Add a new product to the knowledge base.

**Request Body:**
```json
{
  "item_name": "CeraVe Moisturizing Cream",
  "brand": "CeraVe",
  "category": "personal_care",
  "ingredients": ["Water", "Glycerin", "Cetearyl Alcohol", "Ceramide NP"],
  "flagged_ingredients": [],
  "risk_level": "low",
  "recommendation": "Great for sensitive skin",
  "alternative_brand": null,
  "aliases": ["cerave cream", "cerave moisturizer", "cerave lotion"],
  "confidence_source": "verified",
  "notes": "Fragrance-free, dermatologist recommended"
}
```

**Required fields:** `item_name`
**Optional fields:** everything else

**Response (201):** The created object with generated `id`.

---

### PUT /admin/health-items/{item_id}

Update an existing product. Only send the fields you want to change.

**Request Body (partial update):**
```json
{
  "risk_level": "medium",
  "flagged_ingredients": [
    {"name": "New Ingredient", "reason": "recently flagged", "risk": "medium"}
  ]
}
```

**Response (200):** The updated object.
**Error (404):** Item not found.
**Error (400):** No fields provided.

---

### DELETE /admin/health-items/{item_id}

Remove a product from the knowledge base.

**Response (204):** No content.
**Error (404):** Item not found.

---

### GET /admin/unknown-queries

Products users asked about that didn't match the knowledge base. Use this to prioritize what to add next.

| Query Parameter | Type | Default | Description |
|---|---|---|---|
| page | int | 1 | Page number |
| per_page | int | 20 | Items per page (max: 100) |

**Response:**
```json
{
  "data": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "query_text": "Is Cetaphil moisturizer safe?",
      "resolved": false,
      "resolved_item_id": null,
      "timestamp": "2026-03-27T10:00:00Z"
    }
  ],
  "total": 15,
  "page": 1,
  "per_page": 20,
  "pages": 1
}
```

---

### GET /admin/feedback

User feedback on AI responses. Use to identify where the bot fails and iterate.

| Query Parameter | Type | Default | Description |
|---|---|---|---|
| rating | string | null | Filter: `good` or `bad` |
| page | int | 1 | Page number |
| per_page | int | 20 | Items per page (max: 100) |

**Example:**
```bash
curl -H "X-API-Key: key" "http://localhost:8000/admin/feedback?rating=bad"
```

**Response:**
```json
{
  "data": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "message_id": "wamid.xxx",
      "rating": "bad",
      "reason": "incorrect",
      "user_query": "Is Dove soap safe?",
      "ai_response": "This product is safe...",
      "timestamp": "2026-03-27T10:00:00Z"
    }
  ],
  "total": 3,
  "page": 1,
  "per_page": 20,
  "pages": 1
}
```

---

## AI Response Schema

Gemini returns structured JSON enforced via `response_mime_type` + `response_schema` at the API level.

```json
{
  "type": "product_check | general_advice | habit_advice | unclear",
  "verdict": "Safe | Use with caution | Avoid | null",
  "summary": "Main answer in 1-3 sentences",
  "key_ingredients": ["Fragrance", "Parabens"],
  "explanation": "Why it matters (always filled, never null)",
  "suggestion": "Specific actionable improvement (always filled)",
  "follow_up": "Short question, max 8 words",
  "confidence": "high | medium | low"
}
```

### Confidence levels
- **high** - Ingredient list provided or product found in verified database
- **medium** - General product knowledge, no exact data
- **low** - Unclear image, missing data, unfamiliar product

### Response formatting

The formatter converts JSON to WhatsApp text with confidence-based tone:

**High confidence:**
```
[verdict emoji] [Verdict]
[Summary]
Key concerns: [ingredients]
[Explanation]
[Suggestion]
[Follow-up]
```

**Medium confidence** (product checks only):
Appends: "This is based on general knowledge. For a more accurate check, send the ingredient list or a photo."

**Low confidence:**
Appends: "I might be off here - could you share the full ingredient list for a better check?"

### Before/After swap comparison
When a product is found in the KB and has an `alternative_brand` that is also in the DB with a lower risk level, the response includes a clear swap comparison in the suggestion field:
```
Simple swap: Switch from Dettol (high risk) to Mamaearth (low risk) - removes the antimicrobial agent.
```

### Share prompt
Product check responses with high or medium confidence append:
```
Know someone who uses this product? Forward this to them!
```

### Progress feedback
When a user has checked 2+ products, the response may include progress messages:
```
Your average product score went from 48 to 52 (+4)
You've reduced 1 high-risk product(s) from your routine
```

Milestone messages are triggered at: first product, 5 products, average crosses 60, average crosses 80.

Auto-nudge at 3 products: "Type 'my footprint' to see your chemical exposure summary."

### After every reply
The bot sends interactive feedback buttons: "Helpful" / "Not helpful"

---

## Special Commands

These are handled by the backend directly (bypass AI).

### "my footprint" / "my products"

Returns the user's personal chemical footprint computed from all products they've checked.

**Response:**
```
Your Chemical Footprint (12 products)
Average Score: 48/100 (Fair)

Your top exposures:
  Fragrance: in 8 of 12 products (67%)
  SLS: in 4 of 12 products (33%)
  Parabens: in 3 of 12 products (25%)

Highest risk: Pantene Shampoo (Score: 35/100)

Best swap for biggest impact:
  Replace Pantene (35) with WOW Onion Shampoo (82)
  Improvement: +47 points

Recent trend: 42 -> 45 -> 48
```

### "what should I swap" / "swap priority"

Returns personalized swap recommendations ranked by impact.

**Response:**
```
Your Swap Priority (based on 12 products)

1. Pantene Shampoo -> WOW Onion Shampoo
   Score: 35 -> 82 (+47 points)
   Removes: DMDM Hydantoin, SLS

2. Dettol Soap -> Himalaya Neem Soap
   Score: 25 -> 75 (+50 points)
   Removes: Triclocarban

Swapping just #1 and #2 improves your average by ~48 points.
```

### "compare X vs Y"

Compares two products side-by-side with scores.

**Triggers:** "compare", "vs", "versus", "which is better", "which is safer"

**Response:**
```
Product Comparison

Dove Beauty Bar - Score: 80/100 (Good)
  Concerns: Fragrance, BHT

vs

Pears Pure & Gentle - Score: 90/100 (Excellent)
  Concerns: Fragrance, Propylene Glycol

Winner: Pears Pure & Gentle (+10 points)
Pears has fewer concerning ingredients overall.
```

---

### GET /admin/user-footprint/{user_id}

Returns a user's complete chemical footprint.

**Response:**
```json
{
  "total_products": 12,
  "average_score": 48,
  "average_label": "Fair",
  "top_exposures": [
    {"ingredient": "Fragrance", "count": 8, "percentage": 67}
  ],
  "highest_risk_product": {"name": "Pantene Shampoo", "score": 35},
  "best_product": {"name": "Parachute Coconut Oil", "score": 100},
  "best_swap": {
    "current": "Pantene Shampoo",
    "current_score": 35,
    "replacement": "WOW Onion Shampoo",
    "replacement_score": 82,
    "impact": 47
  },
  "score_trend": [42, 45, 48]
}
```

---

### POST /admin/send-daily-tip

Sends today's health tip to all active users via WhatsApp template message. Manual trigger for testing — use cron job in production.

**Response:**
```json
{
  "sent_to": 12,
  "todays_tip": "Quick tip: Check your daily products for 'fragrance' - it can hide 50+ undisclosed chemicals."
}
```

**Note:** Uses template messages (not free-form) since users may not have messaged recently. Requires Meta-approved template.

---

### GET /admin/analytics

Dashboard with key metrics. No query parameters.

**Example:**
```bash
curl -H "X-API-Key: key" http://localhost:8000/admin/analytics
```

**Response:**
```json
{
  "overview": {
    "total_users": 12,
    "total_messages": 240,
    "user_messages": 120,
    "total_products_in_kb": 65
  },
  "quality": {
    "kb_match_rate": "72.5%",
    "kb_matches": 87,
    "kb_misses": 33,
    "satisfaction_rate": "85.0%",
    "good_feedback": 17,
    "bad_feedback": 3
  },
  "action_needed": {
    "unresolved_unknown_queries": 8,
    "top_unknown_queries": ["Cetaphil moisturizer", "Korean glass skin cream"],
    "recent_bad_feedback_reasons": ["incorrect", "generic"]
  }
}
```

**Sections:**
- **overview** - total users, messages, products in KB
- **quality** - KB match rate (% of queries that found a product), satisfaction rate (% positive feedback)
- **action_needed** - unresolved queries to add to KB, reasons for negative feedback
