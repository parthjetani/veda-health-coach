# Veda Admin Dashboard - UI Plan

## Overview

A web dashboard for managing the Veda health coaching chatbot. Connects to the existing backend admin API - zero backend changes needed.

**Who uses it:** You (the admin). Not end users.
**Purpose:** Monitor bot health, manage products, review feedback, grow the knowledge base.

---

## Backend API (Already Built - Ready to Use)

```
GET  /admin/analytics              Dashboard metrics
GET  /admin/users?page=1           User list (paginated)
GET  /admin/health-items?page=1    Product list (filterable by category, risk_level)
POST /admin/health-items           Add product
PUT  /admin/health-items/{id}      Edit product
DELETE /admin/health-items/{id}    Delete product
GET  /admin/unknown-queries?page=1 Unmatched user queries
GET  /admin/feedback?rating=bad    User feedback (filterable by rating)
GET  /health                       Server status
```

All endpoints require `X-API-Key` header.

---

## Tech Stack

| Tool | Why |
|---|---|
| Next.js 14+ (App Router) | React-based, deploys on Vercel for free |
| Tailwind CSS | Fast styling, no design skills needed |
| shadcn/ui | Pre-built tables, forms, cards, buttons - looks professional instantly |
| Recharts | Simple charts for analytics |

**Deploy separately from backend.** Frontend on Vercel, backend on Railway/Render.

---

## Pages (5 total)

### Page 1: Analytics Dashboard (`/`) - P0

The home page. One glance tells you if the bot is healthy.

```
+---------------------------------------------+
|  VEDA ADMIN                    [Server: OK]  |
+----------+----------+----------+-------------+
| 12       | 240      | 72.5%    | 85.0%       |
| Users    | Messages | KB Match | Satisfaction |
+----------+----------+----------+-------------+
|                                              |
|  TOP UNKNOWN QUERIES (action needed)         |
|  +----------------------------------------+  |
|  | Query                    | Asked | Act  |  |
|  |--------------------------|-------|------|  |
|  | Cetaphil moisturizer     | 5x    | [+]  |  |
|  | Korean glass skin cream  | 3x    | [+]  |  |
|  | Himalaya shampoo variant | 2x    | [+]  |  |
|  +----------------------------------------+  |
|                                              |
|  RECENT BAD FEEDBACK                         |
|  +----------------------------------------+  |
|  | Reason    | User Query     | When       |  |
|  |-----------|----------------|------------|  |
|  | incorrect | Is Dove safe?  | 2h ago     |  |
|  | generic   | Check Maggi    | 5h ago     |  |
|  +----------------------------------------+  |
|                                              |
|  PRODUCTS IN KB: 65  |  UNRESOLVED: 8       |
+----------------------------------------------+
```

**API call:** `GET /admin/analytics`

**Components:**
- 4 stat cards (users, messages, KB match rate, satisfaction)
- Unknown queries table (top 10)
- Bad feedback table (recent 10)
- Server health indicator

---

### Page 2: Product Management (`/products`) - P0

Most used page. You'll add/edit products constantly.

#### Product List View

```
+----------------------------------------------+
|  PRODUCTS (65)              [+ Add Product]   |
+----------------------------------------------+
|  Filters: [Category v] [Risk v] [Source v]    |
+------+--------+----------+------+-------------+
| Name | Brand  | Risk     | Src  | Actions     |
+------+--------+----------+------+-------------+
| Dove | Dove   | * medium | vrf  | [Edit][Del] |
| Lux  | Lux    | * medium | vrf  | [Edit][Del] |
| Dettol|Dettol | ! high   | vrf  | [Edit][Del] |
| Amul | Amul   | . low    | vrf  | [Edit][Del] |
+------+--------+----------+------+-------------+
|  < Page 1 of 4 >                              |
+----------------------------------------------+
```

**API calls:** `GET /admin/health-items?page=1&category=personal_care&risk_level=high`

#### Add/Edit Product Form

```
+----------------------------------------------+
|  ADD PRODUCT                                  |
|                                               |
|  Product Name *  [_________________________]  |
|  Brand           [_________________________]  |
|  Category        [Personal Care v          ]  |
|  Risk Level      [Medium v                 ]  |
|                                               |
|  Full Ingredients (one per line):             |
|  [Water                                    ]  |
|  [Sodium Lauryl Sulfate                    ]  |
|  [Fragrance                                ]  |
|  [+ Add ingredient]                           |
|                                               |
|  Flagged Ingredients:                         |
|  [+ Add flagged ingredient]                   |
|  +------------------------------------------+ |
|  | Name      | Reason              | Risk   | |
|  |-----------|---------------------|--------| |
|  | Fragrance | undisclosed chemicals| medium | |
|  | SLS       | strips natural oils | medium | |
|  +------------------------------------------+ |
|                                               |
|  Recommendation  [________________________]   |
|  Alternative     [________________________]   |
|  Aliases         [dove soap, dove bar_____]   |
|  EWG Rating      [___]                        |
|  Notes           [________________________]   |
|                                               |
|  [Cancel]                          [Save]     |
+----------------------------------------------+
```

**API calls:**
- Add: `POST /admin/health-items`
- Edit: `PUT /admin/health-items/{id}`
- Delete: `DELETE /admin/health-items/{id}`

---

### Page 3: Unknown Queries (`/unknown-queries`) - P1

The growth engine. Shows what products users are asking about that aren't in your KB.

```
+----------------------------------------------+
|  UNKNOWN QUERIES (23 unresolved)              |
+----------------------------------------------+
|  [ ] Show resolved                            |
+--------------------------+------+-------------+
| Query                    | When | Action      |
+--------------------------+------+-------------+
| Is Cetaphil safe?        | 2h   | [Add to KB] |
| Check this sunscreen     | 5h   | [Dismiss]   |
| Is Himalaya shampoo ok?  | 1d   | [Add to KB] |
| Korean glass skin cream  | 1d   | [Dismiss]   |
| Mamaearth vitamin C      | 2d   | [Add to KB] |
+--------------------------+------+-------------+
```

**"Add to KB" flow:**
1. Click [Add to KB]
2. Opens Add Product form
3. Product name pre-filled from query text
4. Admin fills in ingredients, risk level, etc.
5. On save, unknown query marked as `resolved = true`

**API calls:**
- List: `GET /admin/unknown-queries`
- Then: `POST /admin/health-items` (to add)

---

### Page 4: Feedback Review (`/feedback`) - P1

Shows where the bot fails. Directly drives prompt and data improvements.

```
+----------------------------------------------+
|  FEEDBACK                [All v] [Bad only v] |
+--------+--------+-----------+-----------------+
| Rating | Reason | User Said | Bot Replied     |
+--------+--------+-----------+-----------------+
| Bad    | wrong  | Is Dove   | This product is |
|        |        | safe?     | safe for daily...|
+--------+--------+-----------+-----------------+
| Bad    | generic| Check     | I don't have    |
|        |        | Maggi     | this product... |
+--------+--------+-----------+-----------------+
| Good   | -      | Is BPA    | BPA is a chemi- |
|        |        | harmful?  | cal found in... |
+--------+--------+-----------+-----------------+
|  < Page 1 of 2 >                              |
+----------------------------------------------+
```

**Click to expand:** Shows full user query + full bot response side by side.

**API calls:** `GET /admin/feedback?rating=bad&page=1`

---

### Page 5: Users (`/users`) - P2

Least urgent - Supabase dashboard already shows this.

```
+----------------------------------------------+
|  USERS (12)                                   |
+------------------+--------+-------------------+
| WhatsApp         | Active | Joined            |
+------------------+--------+-------------------+
| +91 99134*****   | Yes    | Mar 27, 2026      |
| +91 88765*****   | Yes    | Mar 27, 2026      |
| +91 77654*****   | Yes    | Mar 26, 2026      |
+------------------+--------+-------------------+
```

**API calls:** `GET /admin/users?page=1`

---

## Navigation (Sidebar)

```
+------------------+------------------------------+
|  VEDA ADMIN      |                              |
|                  |     [Page Content]            |
|  > Dashboard     |                              |
|    Products (65) |                              |
|    Unknown (23)  |                              |
|    Feedback (20) |                              |
|    Users (12)    |                              |
|                  |                              |
|  Server: OK      |                              |
+------------------+------------------------------+
```

- Badge counts on sidebar items (products total, unresolved unknowns, feedback count)
- Server health indicator at bottom (pings `GET /health` every 30 seconds)

---

## Project Structure

```
veda-admin/
|-- app/
|   |-- page.tsx                    # Dashboard (analytics)
|   |-- layout.tsx                  # Sidebar + header
|   |-- products/
|   |   |-- page.tsx                # Product list
|   |   |-- new/page.tsx            # Add product form
|   |   |-- [id]/edit/page.tsx      # Edit product form
|   |-- unknown-queries/
|   |   |-- page.tsx                # Unknown queries list
|   |-- feedback/
|   |   |-- page.tsx                # Feedback list
|   |-- users/
|   |   |-- page.tsx                # User list
|
|-- lib/
|   |-- api.ts                      # API client (all fetch calls)
|   |-- types.ts                    # TypeScript types matching backend models
|
|-- components/
|   |-- sidebar.tsx                 # Navigation sidebar
|   |-- stats-card.tsx              # Metric card (number + label)
|   |-- data-table.tsx              # Reusable paginated table
|   |-- product-form.tsx            # Add/edit product form
|   |-- flagged-ingredient-input.tsx # Dynamic list for flagged ingredients
|   |-- pagination.tsx              # Page controls
|
|-- .env.local                      # NEXT_PUBLIC_API_URL + ADMIN_API_KEY
|-- package.json
|-- tailwind.config.js
|-- next.config.js
```

---

## API Client

```typescript
// lib/api.ts

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const KEY = process.env.ADMIN_API_KEY || '';

async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      'X-API-Key': KEY,
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// Analytics
export const getAnalytics = () => api('/admin/analytics');

// Products
export const getProducts = (page = 1, category?: string, risk?: string) => {
  const params = new URLSearchParams({ page: String(page) });
  if (category) params.set('category', category);
  if (risk) params.set('risk_level', risk);
  return api(`/admin/health-items?${params}`);
};
export const createProduct = (data: any) =>
  api('/admin/health-items', { method: 'POST', body: JSON.stringify(data) });
export const updateProduct = (id: string, data: any) =>
  api(`/admin/health-items/${id}`, { method: 'PUT', body: JSON.stringify(data) });
export const deleteProduct = (id: string) =>
  api(`/admin/health-items/${id}`, { method: 'DELETE' });

// Unknown Queries
export const getUnknownQueries = (page = 1) =>
  api(`/admin/unknown-queries?page=${page}`);

// Feedback
export const getFeedback = (page = 1, rating?: string) => {
  const params = new URLSearchParams({ page: String(page) });
  if (rating) params.set('rating', rating);
  return api(`/admin/feedback?${params}`);
};

// Users
export const getUsers = (page = 1) => api(`/admin/users?page=${page}`);

// Health
export const getHealth = () => api('/health');
```

---

## TypeScript Types

```typescript
// lib/types.ts

interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

interface Analytics {
  overview: {
    total_users: number;
    total_messages: number;
    user_messages: number;
    total_products_in_kb: number;
  };
  quality: {
    kb_match_rate: string;
    kb_matches: number;
    kb_misses: number;
    satisfaction_rate: string;
    good_feedback: number;
    bad_feedback: number;
  };
  action_needed: {
    unresolved_unknown_queries: number;
    top_unknown_queries: string[];
    recent_bad_feedback_reasons: string[];
  };
}

interface FlaggedIngredient {
  name: string;
  reason: string;
  risk: 'high' | 'medium' | 'low';
}

interface HealthItem {
  id: string;
  item_name: string;
  brand: string | null;
  category: 'food' | 'supplement' | 'personal_care' | 'household' | 'other' | null;
  ingredients: string[];
  flagged_ingredients: FlaggedIngredient[];
  risk_level: 'high' | 'medium' | 'low' | null;
  recommendation: string | null;
  alternative_brand: string | null;
  aliases: string[];
  confidence_source: 'verified' | 'inferred' | 'community';
  ewg_rating: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

interface UnknownQuery {
  id: string;
  user_id: string;
  query_text: string;
  resolved: boolean;
  resolved_item_id: string | null;
  timestamp: string;
}

interface Feedback {
  id: string;
  user_id: string;
  message_id: string;
  rating: 'good' | 'bad';
  reason: string | null;
  user_query: string | null;
  ai_response: string | null;
  timestamp: string;
}

interface User {
  id: string;
  whatsapp_number: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
```

---

## CORS Configuration

The backend already has CORS middleware in `app/main.py`. In development mode, it allows all origins. For production, update to allow your Vercel domain:

```python
# app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://veda-admin.vercel.app"] if settings.is_production else ["*"],
    ...
)
```

---

## Environment Variables

```bash
# veda-admin/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000      # or production URL
ADMIN_API_KEY=your-admin-api-key
```

**Security note:** `ADMIN_API_KEY` should NOT be in `NEXT_PUBLIC_` prefix - it should be server-side only. Use Next.js API routes as a proxy, or keep it client-side for internal-only tools.

---

## Build Order

| Day | What | Priority |
|---|---|---|
| Day 1 | Project setup + API client + layout (sidebar) | Foundation |
| Day 2 | Analytics dashboard page | P0 |
| Day 3 | Product list + filters + pagination | P0 |
| Day 4 | Add/edit product form | P0 |
| Day 5 | Unknown queries page + "Add to KB" flow | P1 |
| Day 6 | Feedback review page | P1 |
| Day 7 | Users page + polish + deploy to Vercel | P2 |

---

## What NOT to Build

- Login/auth system (API key in env is enough - you're the only admin)
- Real-time WebSocket updates (polling every 30 seconds is fine)
- Mobile responsive layout (you'll use this on desktop only)
- Complex data visualizations (simple numbers + tables are enough)
- Dark mode (waste of time for an internal tool)
- Export/import features (use Supabase dashboard for bulk operations)

---

## Deployment

1. Push `veda-admin/` to GitHub
2. Go to [vercel.com](https://vercel.com) -> Import from GitHub
3. Set environment variables (`NEXT_PUBLIC_API_URL`, `ADMIN_API_KEY`)
4. Deploy - Vercel handles everything
5. Update CORS in backend to allow your Vercel domain

Frontend and backend are completely separate deployments.
