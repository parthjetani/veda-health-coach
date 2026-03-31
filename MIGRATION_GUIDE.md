# Veda - Migration Guide

How to swap major components. Each section is independent - do them in any order.

Recommended order if doing all three: LLM swap first (smallest) -> Messenger (independent) -> Database (most files)

---

## 1. Swap AI Provider (Gemini -> Claude / OpenAI / Other)

### Current State
- Google Gemini 2.5 Flash via `google-genai` SDK
- Structured JSON enforced via `response_schema` at API level
- Single file: `app/services/ai_engine.py`

### What Changes

**Only 4 files need changes. The rest of the system never touches the AI directly.**

#### Step 1: Dependencies

```bash
# For Claude:
# Remove: google-genai==1.14.0
# Add:    anthropic==0.42.0

# For OpenAI:
# Remove: google-genai==1.14.0
# Add:    openai==1.52.0
```

#### Step 2: Config (`app/config.py`)

Replace the Gemini section:

```python
# CURRENT (Gemini)
gemini_api_key: str
gemini_model: str = "gemini-2.5-flash"
gemini_max_tokens: int = 1024
gemini_temperature: float = 0.3

# CLAUDE REPLACEMENT
anthropic_api_key: str
claude_model: str = "claude-sonnet-4-6"
claude_max_tokens: int = 1024
claude_temperature: float = 0.3

# OPENAI REPLACEMENT
openai_api_key: str
openai_model: str = "gpt-4o"
openai_max_tokens: int = 1024
openai_temperature: float = 0.3
```

#### Step 3: Main (`app/main.py`)

Replace the client initialization in lifespan:

```python
# CURRENT (Gemini)
from google import genai
app.state.gemini_client = genai.Client(api_key=settings.gemini_api_key)

# CLAUDE REPLACEMENT
from anthropic import AsyncAnthropic
app.state.ai_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

# OPENAI REPLACEMENT
from openai import AsyncOpenAI
app.state.ai_client = AsyncOpenAI(api_key=settings.openai_api_key)
```

Also update the AIEngine instantiation in `app/api/webhooks/whatsapp.py`:
```python
ai_engine = AIEngine(
    client=request.app.state.ai_client,  # was gemini_client
    settings=settings,
    base_system_prompt=request.app.state.system_prompt,
)
```

#### Step 4: AI Engine (`app/services/ai_engine.py`) - Full Rewrite

The interface stays the same. Only the internals change.

**Public interface (unchanged):**
```python
class AIEngine:
    async def get_response(
        self,
        user_message: str,
        conversation_history: list[dict],
        product_context: str | None = None,
        source_context: str | None = None,
        image_base64: str | None = None,
        image_mime_type: str | None = None,
    ) -> str:
```

**Claude implementation:**
```python
from anthropic import AsyncAnthropic

class AIEngine:
    def __init__(self, client: AsyncAnthropic, settings, base_system_prompt: str):
        self.client = client
        self.model = settings.claude_model
        self.max_tokens = settings.claude_max_tokens
        self.temperature = settings.claude_temperature
        self.base_system_prompt = base_system_prompt

    def _validate_history(self, history: list[dict]) -> list[dict]:
        # Claude uses "assistant" role (same as DB storage)
        # Must alternate user/assistant strictly
        # First message must be "user"
        # Merge consecutive same-role messages
        # (Same logic as current, but role stays "assistant" not "model")

    def _build_user_content(self, user_message, image_base64, image_mime_type):
        if not image_base64:
            return user_message
        # Claude vision format:
        return [
            {"type": "image", "source": {"type": "base64", "media_type": image_mime_type, "data": image_base64}},
            {"type": "text", "text": user_message or "Please analyze this product label."}
        ]

    async def get_response(self, ...):
        system_prompt = self._build_system_prompt(product_context, source_context)
        history = self._validate_history(conversation_history)
        user_content = self._build_user_content(user_message, image_base64, image_mime_type)
        messages = history + [{"role": "user", "content": user_content}]

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,  # Claude has native system parameter
            messages=messages,
        )
        return response.content[0].text
```

**OpenAI implementation:**
```python
from openai import AsyncOpenAI

class AIEngine:
    def __init__(self, client: AsyncOpenAI, settings, base_system_prompt: str):
        self.client = client
        self.model = settings.openai_model
        self.max_tokens = settings.openai_max_tokens
        self.temperature = settings.openai_temperature
        self.base_system_prompt = base_system_prompt

    def _validate_history(self, history: list[dict]) -> list[dict]:
        # OpenAI uses "assistant" role (same as Claude)
        # Same alternation rules

    def _build_user_content(self, user_message, image_base64, image_mime_type):
        if not image_base64:
            return user_message
        # OpenAI vision format:
        return [
            {"type": "image_url", "image_url": {"url": f"data:{image_mime_type};base64,{image_base64}"}},
            {"type": "text", "text": user_message or "Please analyze this product label."}
        ]

    async def get_response(self, ...):
        system_prompt = self._build_system_prompt(product_context, source_context)
        history = self._validate_history(conversation_history)
        user_content = self._build_user_content(user_message, image_base64, image_mime_type)

        messages = [{"role": "system", "content": system_prompt}]
        messages += history
        messages += [{"role": "user", "content": user_content}]

        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            response_format={"type": "json_object"},  # OpenAI JSON mode
            messages=messages,
        )
        return response.choices[0].message.content
```

### Key Differences Between Providers

| Feature | Gemini | Claude | OpenAI |
|---|---|---|---|
| System prompt | `system_instruction` param | `system` param | First message with role "system" |
| JSON enforcement | `response_schema` (API-level) | Prompt-only (no API enforcement) | `response_format: json_object` |
| Vision format | `Part.from_bytes(data, mime_type)` | `{"type": "image", "source": {"type": "base64", ...}}` | `{"type": "image_url", "image_url": {"url": "data:...;base64,..."}}` |
| History roles | user / model | user / assistant | user / assistant |
| Async client | `client.aio.models.generate_content()` | `client.messages.create()` | `client.chat.completions.create()` |
| Free tier | 15 req/min, 1500/day | No free tier ($5 minimum) | $5 free credit for new accounts |

### Important: JSON Enforcement

Gemini currently enforces JSON via `response_schema` at API level. Claude does NOT have this.

If switching to Claude:
- JSON enforcement relies entirely on the system prompt
- The prompt already has strict JSON rules
- But Claude may occasionally return plain text for conversational messages
- The `response_formatter.py` fallback (strip markdown, send raw text) handles this

OpenAI's `response_format: json_object` is reliable but less strict than Gemini's full schema.

### Multi-Provider Architecture (Optional)

To support switching between providers via config:

```
app/services/
|-- ai_engine.py          # Base protocol / interface
|-- ai_gemini.py          # Gemini implementation
|-- ai_claude.py          # Claude implementation
|-- ai_openai.py          # OpenAI implementation
```

`app/config.py`:
```python
ai_provider: str = "gemini"  # or "claude" or "openai"
ai_api_key: str              # single key field
ai_model: str = "gemini-2.5-flash"
```

`app/main.py`:
```python
if settings.ai_provider == "gemini":
    from app.services.ai_gemini import GeminiEngine as Engine
elif settings.ai_provider == "claude":
    from app.services.ai_claude import ClaudeEngine as Engine
elif settings.ai_provider == "openai":
    from app.services.ai_openai import OpenAIEngine as Engine

app.state.ai_engine = Engine(api_key=settings.ai_api_key, ...)
```

---

## 2. Swap Database (Supabase -> Direct PostgreSQL)

### Current State
- Supabase Python client (`supabase-py`)
- All queries use `supabase.table("x").select().eq().execute()` pattern
- Schema is standard PostgreSQL (runs anywhere)
- `search_health_items()` is a PostgreSQL stored function

### What Changes

**~15 files change, but it's mechanical - same queries, different syntax.**

#### Step 1: Dependencies

```bash
# Remove: supabase==2.11.0
# Add:    asyncpg==0.30.0
#         sqlalchemy[asyncio]==2.0.36
```

#### Step 2: Config (`app/config.py`)

```python
# CURRENT (Supabase)
supabase_url: str
supabase_service_role_key: str

# POSTGRESQL REPLACEMENT
database_url: str  # postgresql+asyncpg://user:password@host:5432/dbname
```

#### Step 3: Client (`app/db/client.py`)

```python
# CURRENT
from supabase import create_client
supabase = create_client(url, key)

# POSTGRESQL REPLACEMENT
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = create_async_engine(settings.database_url)
async_session = async_sessionmaker(engine, class_=AsyncSession)
```

#### Step 4: Main (`app/main.py`)

```python
# CURRENT
app.state.supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)

# POSTGRESQL REPLACEMENT
from app.db.client import engine, async_session
app.state.db_session = async_session

# In lifespan cleanup:
await engine.dispose()
```

#### Step 5: Query Files (all 6 files in `app/db/queries/`)

Every query changes syntax but keeps the same logic.

Example - `get_user_by_whatsapp`:

```python
# CURRENT (Supabase)
async def get_user_by_whatsapp(supabase, whatsapp_number):
    result = supabase.table("users").select("*").eq("whatsapp_number", whatsapp_number).limit(1).execute()
    rows = result.data or []
    return rows[0] if rows else None

# POSTGRESQL REPLACEMENT (SQLAlchemy)
async def get_user_by_whatsapp(session: AsyncSession, whatsapp_number: str):
    result = await session.execute(
        text("SELECT * FROM users WHERE whatsapp_number = :num LIMIT 1"),
        {"num": whatsapp_number}
    )
    row = result.mappings().first()
    return dict(row) if row else None

# OR with raw asyncpg:
async def get_user_by_whatsapp(pool, whatsapp_number: str):
    row = await pool.fetchrow("SELECT * FROM users WHERE whatsapp_number = $1", whatsapp_number)
    return dict(row) if row else None
```

Example - `search_health_items`:
```python
# CURRENT (Supabase RPC)
result = supabase.rpc("search_health_items", {"query": query, "match_threshold": threshold}).execute()

# POSTGRESQL REPLACEMENT (direct SQL)
result = await session.execute(
    text("SELECT * FROM search_health_items(:query, :threshold)"),
    {"query": query, "threshold": threshold}
)
return [dict(row) for row in result.mappings()]
```

#### Step 6: All files using `request.app.state.supabase`

Replace with `request.app.state.db_session`:
- `app/api/webhooks/whatsapp.py`
- `app/api/admin/users.py`
- `app/api/admin/health_items.py`
- `app/core/message_handler.py` (passed as parameter)
- `app/core/feedback_handler.py`

#### Migrations

**No changes needed.** The `migrations/*.sql` files are already standard PostgreSQL. They work on any PostgreSQL database, not just Supabase.

### What You Lose Without Supabase

| Feature | Supabase | Self-hosted PostgreSQL |
|---|---|---|
| Dashboard UI | Built-in table editor | Need pgAdmin or similar |
| Auth | Built-in (not used) | N/A |
| Real-time | Built-in (not used) | N/A |
| Free hosting | 500MB free | Need to pay for hosting |
| RLS | Managed | Manual setup |
| Backups | Automatic | Manual |

### Recommended PostgreSQL Hosting

| Provider | Free Tier | Notes |
|---|---|---|
| Supabase | 500MB, 2 projects | Current choice, easiest |
| Neon | 512MB, branching | Good free tier, serverless |
| Railway | 1GB, $5 free credit | Same platform as deployment |
| Render | 256MB, 90 day limit | Expires after 90 days |
| Self-hosted | Unlimited | VPS like DigitalOcean $6/mo |

---

## 3. Add Facebook Messenger

### Current State
- WhatsApp only
- Single webhook endpoint
- User identified by phone number
- WhatsApp-specific features (template messages, 24h window, interactive buttons)

### What to Build

#### New Files (6 files)

**`app/api/webhooks/messenger.py`** - Webhook endpoint
```python
# GET  /webhook/messenger  - Meta verification (same pattern as WhatsApp)
# POST /webhook/messenger  - Receive messages

# Messenger webhook payload structure:
# {
#   "object": "page",
#   "entry": [{
#     "messaging": [{
#       "sender": {"id": "PSID"},
#       "message": {"text": "hello"} or {"attachments": [{...}]}
#     }]
#   }]
# }

# Key difference: entry[].messaging[] (not entry[].changes[].value.messages[])
```

**`app/services/messenger_client.py`** - Send messages
```python
class MessengerClient:
    # Base URL: https://graph.facebook.com/v21.0/me/messages
    # Auth: Page Access Token (different from WhatsApp token)

    async def send_text_message(self, recipient_id: str, text: str):
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": text}
        }

    async def send_quick_replies(self, recipient_id: str, text: str, replies: list):
        # Messenger equivalent of WhatsApp interactive buttons
        payload = {
            "recipient": {"id": recipient_id},
            "message": {
                "text": text,
                "quick_replies": [
                    {"content_type": "text", "title": "Helpful", "payload": "feedback_good"},
                    {"content_type": "text", "title": "Not helpful", "payload": "feedback_bad"}
                ]
            }
        }

    async def get_media_url(self, attachment_url: str) -> str:
        # Messenger provides direct URL (no media ID lookup needed)
        return attachment_url

    async def download_media(self, url: str) -> bytes:
        # Direct download (no Bearer token needed, unlike WhatsApp)
```

**`app/models/messenger.py`** - Webhook payload models
```python
class MessengerMessage(BaseModel):
    mid: str | None = None        # message ID
    text: str | None = None       # text content
    attachments: list | None = None  # images, files

class MessengerSender(BaseModel):
    id: str                       # Page-Scoped User ID (PSID)

class MessengerMessaging(BaseModel):
    sender: MessengerSender
    message: MessengerMessage | None = None
    postback: dict | None = None  # button clicks

class MessengerEntry(BaseModel):
    messaging: list[MessengerMessaging]

class MessengerWebhook(BaseModel):
    object: str
    entry: list[MessengerEntry]
```

**`migrations/006_messenger.sql`** (next available migration number)
```sql
-- Add Messenger support to users table
ALTER TABLE users ADD COLUMN messenger_user_id text UNIQUE;
ALTER TABLE users ADD COLUMN preferred_channel text NOT NULL DEFAULT 'whatsapp'
    CHECK (preferred_channel IN ('whatsapp', 'messenger'));

-- Index for Messenger user lookup
CREATE INDEX idx_users_messenger_id ON users(messenger_user_id);
```

#### Modified Files (6 files)

**`app/config.py`** - Add Messenger config
```python
# Add:
messenger_page_access_token: str = ""  # optional, empty if not using Messenger
messenger_verify_token: str = ""
messenger_app_secret: str = ""         # for webhook signature verification
```

**`app/main.py`** - Register Messenger router
```python
from app.api.webhooks.messenger import router as messenger_router
app.include_router(messenger_router, prefix="/webhook/messenger", tags=["Messenger"])
```

**`app/db/queries/users.py`** - Add Messenger user functions
```python
async def get_user_by_messenger_id(supabase, messenger_id: str) -> dict | None:
    ...

async def get_or_create_messenger_user(supabase, messenger_id: str) -> dict:
    ...
```

**`app/core/message_handler.py`** - Accept channel parameter
```python
async def handle_incoming_message(
    user_identifier: str,          # phone number OR messenger PSID
    channel: str,                  # "whatsapp" or "messenger"
    message_text: str | None,
    message_type: str,
    message_id: str | None,
    media_id: str | None,          # WhatsApp media ID
    media_url: str | None,         # Messenger direct URL
    media_mime_type: str | None,
    supabase,
    messaging_client,              # WhatsAppClient or MessengerClient (polymorphic)
    ai_engine,
    settings,
):
    # User lookup changes based on channel:
    if channel == "whatsapp":
        user = await get_or_create_user(supabase, user_identifier)
    else:
        user = await get_or_create_messenger_user(supabase, user_identifier)

    # Media download changes:
    if media_id:   # WhatsApp: need to get URL first
        url = await messaging_client.get_media_url(media_id)
        bytes = await messaging_client.download_media(url)
    elif media_url: # Messenger: URL provided directly
        bytes = await messaging_client.download_media(media_url)

    # Everything else stays the same:
    # KB lookup, AI call, format, send reply
    # messaging_client.send_text_message() works for both
```

**`app/core/feedback_handler.py`** - Accept channel parameter
```python
# Same pattern - accept messaging_client instead of whatsapp_client
```

### WhatsApp vs Messenger: Key Differences

| Feature | WhatsApp | Messenger |
|---|---|---|
| User ID | Phone number (E.164) | Page-Scoped User ID (PSID) |
| Send endpoint | `/{phone_id}/messages` | `/me/messages` |
| Auth | System User token | Page Access Token |
| Media access | Bearer token + media ID lookup | Direct URL download |
| Buttons | Interactive reply buttons | Quick replies |
| 24h window | Strict (requires templates) | More relaxed |
| Webhook payload | `entry[].changes[].value.messages[]` | `entry[].messaging[].message` |
| Webhook verify | `hub.verify_token` | Same pattern |
| Signature verify | Not required | `X-Hub-Signature-256` (recommended) |
| Setup | WhatsApp Business API | Facebook Page + Developer App |

### Messenger Setup (Meta Dashboard)

1. In your existing Meta App, click **Add Product** -> **Messenger** -> **Set Up**
2. Connect a **Facebook Page** (create one if needed, e.g., "Veda Health Coach")
3. Get **Page Access Token** from Messenger Settings
4. Configure webhook: `https://your-domain.com/webhook/messenger`
5. Subscribe to: `messages`, `messaging_postbacks`
6. Users can now message your Facebook Page and get AI responses

### Files NOT Changed

These files work for both channels without modification:
- `app/services/ai_engine.py` - AI doesn't care about channel
- `app/services/knowledge_base.py` - Product lookup is channel-agnostic
- `app/services/source_context.py` - Same citations
- `app/services/conversation.py` - Same conversation storage
- `app/core/response_formatter.py` - Same formatting
- `app/models/ai_response.py` - Same AI response schema
- `app/models/admin.py` - Same admin models
- `prompts/health_coach.txt` - Same prompt
- `tests/` - Existing tests still pass (add new tests for Messenger)

---

## Migration Effort Summary

| Change | New Files | Modified Files | Effort | Can Do Independently |
|---|---|---|---|---|
| Gemini -> Claude/OpenAI | 0 (rewrite 1) | 3 | Small (1-2 hours) | Yes |
| Supabase -> PostgreSQL | 0 (rewrite ~8) | 7 | Medium (4-6 hours) | Yes |
| Add Messenger | 4 | 6 | Medium-High (6-8 hours) | Yes |
| All three | 4 | ~16 | 1-2 days | Do in sequence |

## When to Do Each

| Change | When | Why |
|---|---|---|
| Swap LLM | When you need it (cost, quality, features) | Current Gemini free tier works fine |
| Add Messenger | After WhatsApp is stable + Meta verified | Don't split focus before WhatsApp works perfectly |
| Swap DB | Only if Supabase limits hit or self-hosting needed | Supabase free tier is sufficient for 1000+ users |
