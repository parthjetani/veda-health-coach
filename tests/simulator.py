"""
Conversation simulator for Veda health coaching chatbot.

Provides MockSupabase, MockGemini, MockWhatsApp, and ConversationSimulator
to run end-to-end tests through the real message_handler pipeline with
fully in-memory mocked external services.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Environment variables (must be set before importing any app modules)
# ---------------------------------------------------------------------------
os.environ.setdefault("WHATSAPP_ACCESS_TOKEN", "test-token")
os.environ.setdefault("WHATSAPP_PHONE_NUMBER_ID", "123456789")
os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", "test-verify-token")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ["ADMIN_API_KEY"] = "test-admin-key"

from app.config import Settings, get_settings

get_settings.cache_clear()

# ---------------------------------------------------------------------------
# Test products matching real seed data structure
# ---------------------------------------------------------------------------
TEST_PRODUCTS = [
    {
        "id": "dove-1",
        "item_name": "Dove Beauty Bar",
        "brand": "Dove",
        "category": "personal_care",
        "ingredients": ["Sodium Lauroyl Isethionate", "Fragrance", "BHT"],
        "flagged_ingredients": [
            {"name": "Fragrance", "reason": "undisclosed chemicals", "risk": "medium"},
            {"name": "BHT", "reason": "preservative", "risk": "low"},
        ],
        "risk_level": "medium",
        "recommendation": "Switch to fragrance-free",
        "alternative_brand": "Pears Pure & Gentle",
        "aliases": ["dove soap", "dove bar"],
        "confidence_source": "verified",
        "ewg_rating": "4",
        "notes": "Contains fragrance",
    },
    {
        "id": "pears-1",
        "item_name": "Pears Pure & Gentle",
        "brand": "Pears",
        "category": "personal_care",
        "ingredients": ["Glycerin", "Sodium Palmate", "Water"],
        "flagged_ingredients": [],
        "risk_level": "low",
        "recommendation": "Good choice",
        "alternative_brand": None,
        "aliases": ["pears soap", "pears"],
        "confidence_source": "verified",
        "ewg_rating": "1",
        "notes": "Glycerin-based, gentle formula",
    },
    {
        "id": "dettol-1",
        "item_name": "Dettol Original Soap",
        "brand": "Dettol",
        "category": "personal_care",
        "ingredients": ["Triclosan", "Sodium Lauryl Sulfate", "Fragrance", "BHT"],
        "flagged_ingredients": [
            {"name": "Triclosan", "reason": "antimicrobial resistance", "risk": "high"},
            {"name": "Sodium Lauryl Sulfate", "reason": "skin irritant", "risk": "medium"},
            {"name": "Fragrance", "reason": "undisclosed chemicals", "risk": "medium"},
        ],
        "risk_level": "high",
        "recommendation": "Avoid - contains triclosan",
        "alternative_brand": "Pears Pure & Gentle",
        "aliases": ["dettol soap", "dettol"],
        "confidence_source": "verified",
        "ewg_rating": "7",
        "notes": "High concern due to triclosan",
    },
    {
        "id": "pantene-1",
        "item_name": "Pantene Pro-V Shampoo",
        "brand": "Pantene",
        "category": "hair_care",
        "ingredients": ["Sodium Laureth Sulfate", "Dimethicone", "Fragrance", "Methylparaben"],
        "flagged_ingredients": [
            {"name": "Sodium Laureth Sulfate", "reason": "irritant", "risk": "medium"},
            {"name": "Fragrance", "reason": "undisclosed chemicals", "risk": "medium"},
            {"name": "Methylparaben", "reason": "endocrine disruptor", "risk": "high"},
        ],
        "risk_level": "high",
        "recommendation": "Switch to sulfate-free shampoo",
        "alternative_brand": "WOW Onion Shampoo",
        "aliases": ["pantene shampoo", "pantene"],
        "confidence_source": "verified",
        "ewg_rating": "6",
        "notes": "Contains sulfates and parabens",
    },
    {
        "id": "nivea-1",
        "item_name": "Nivea Soft Cream",
        "brand": "Nivea",
        "category": "personal_care",
        "ingredients": ["Aqua", "Mineral Oil", "Glycerin"],
        "flagged_ingredients": [
            {"name": "Mineral Oil", "reason": "petroleum-derived", "risk": "low"},
        ],
        "risk_level": "low",
        "recommendation": "Generally safe for most",
        "alternative_brand": None,
        "aliases": ["nivea cream", "nivea"],
        "confidence_source": "verified",
        "ewg_rating": "2",
        "notes": "Mild formula",
    },
    {
        "id": "parachute-1",
        "item_name": "Parachute Coconut Oil",
        "brand": "Parachute",
        "category": "hair_care",
        "ingredients": ["100% Coconut Oil"],
        "flagged_ingredients": [],
        "risk_level": "low",
        "recommendation": "Excellent natural choice",
        "alternative_brand": None,
        "aliases": ["parachute oil", "parachute"],
        "confidence_source": "verified",
        "ewg_rating": "1",
        "notes": "Single ingredient, pure coconut oil",
    },
    {
        "id": "wow-1",
        "item_name": "WOW Onion Shampoo",
        "brand": "WOW Skin Science",
        "category": "hair_care",
        "ingredients": ["Onion Seed Oil Extract", "Aqua", "Pro-Vitamin B5"],
        "flagged_ingredients": [
            {"name": "Fragrance", "reason": "natural fragrance blend", "risk": "low"},
        ],
        "risk_level": "low",
        "recommendation": "Good sulfate-free option",
        "alternative_brand": None,
        "aliases": ["wow shampoo", "wow onion"],
        "confidence_source": "verified",
        "ewg_rating": "2",
        "notes": "Sulfate-free formula",
    },
    {
        "id": "mamaearth-1",
        "item_name": "Mamaearth Vitamin C Face Wash",
        "brand": "Mamaearth",
        "category": "personal_care",
        "ingredients": ["Vitamin C", "Turmeric", "Aqua"],
        "flagged_ingredients": [
            {"name": "Fragrance", "reason": "contains natural fragrance", "risk": "low"},
        ],
        "risk_level": "low",
        "recommendation": "Good option for most skin types",
        "alternative_brand": None,
        "aliases": ["mamaearth face wash", "mamaearth"],
        "confidence_source": "verified",
        "ewg_rating": "2",
        "notes": "Natural ingredients",
    },
    {
        "id": "colgate-1",
        "item_name": "Colgate Total Toothpaste",
        "brand": "Colgate",
        "category": "oral_care",
        "ingredients": ["Sodium Fluoride", "Triclosan", "Sorbitol"],
        "flagged_ingredients": [
            {"name": "Triclosan", "reason": "antimicrobial resistance", "risk": "high"},
            {"name": "Sodium Lauryl Sulfate", "reason": "irritant", "risk": "low"},
        ],
        "risk_level": "medium",
        "recommendation": "Consider triclosan-free options",
        "alternative_brand": None,
        "aliases": ["colgate total", "colgate toothpaste"],
        "confidence_source": "verified",
        "ewg_rating": "5",
        "notes": "Contains triclosan",
    },
    {
        "id": "lux-1",
        "item_name": "Lux Soft Touch Soap",
        "brand": "Lux",
        "category": "personal_care",
        "ingredients": ["Sodium Palmate", "Fragrance", "BHT"],
        "flagged_ingredients": [
            {"name": "Fragrance", "reason": "undisclosed chemicals", "risk": "medium"},
            {"name": "BHT", "reason": "preservative", "risk": "low"},
        ],
        "risk_level": "medium",
        "recommendation": "Switch to fragrance-free soap",
        "alternative_brand": "Pears Pure & Gentle",
        "aliases": ["lux soap", "lux"],
        "confidence_source": "verified",
        "ewg_rating": "4",
        "notes": "Contains synthetic fragrance",
    },
]

# ---------------------------------------------------------------------------
# Pre-configured Gemini responses keyed by keyword
# ---------------------------------------------------------------------------
GEMINI_RESPONSES = {
    "dove": {
        "type": "product_check",
        "verdict": "Use with caution",
        "summary": "Dove Beauty Bar contains fragrance which may hide undisclosed chemicals.",
        "key_ingredients": ["Fragrance", "BHT"],
        "explanation": "Fragrance can contain undisclosed chemicals that may irritate sensitive skin.",
        "suggestion": "Try fragrance-free options like Pears Pure & Gentle.",
        "follow_up": "Want safer alternatives?",
        "confidence": "high",
    },
    "pears": {
        "type": "product_check",
        "verdict": "Safe",
        "summary": "Pears Pure & Gentle is a clean, glycerin-based soap with no major concerns.",
        "key_ingredients": [],
        "explanation": "No flagged ingredients found. Glycerin is gentle on skin.",
        "suggestion": "Good choice for everyday use.",
        "follow_up": "Want to check another product?",
        "confidence": "high",
    },
    "dettol": {
        "type": "product_check",
        "verdict": "Avoid",
        "summary": "Dettol Original Soap contains triclosan, a concerning antimicrobial agent.",
        "key_ingredients": ["Triclosan", "Sodium Lauryl Sulfate", "Fragrance"],
        "explanation": "Triclosan is linked to antimicrobial resistance and thyroid disruption.",
        "suggestion": "Switch to Pears Pure & Gentle for a safer alternative.",
        "follow_up": "Want me to compare alternatives?",
        "confidence": "high",
    },
    "pantene": {
        "type": "product_check",
        "verdict": "Avoid",
        "summary": "Pantene Pro-V Shampoo contains sulfates, parabens, and fragrance.",
        "key_ingredients": ["Sodium Laureth Sulfate", "Fragrance", "Methylparaben"],
        "explanation": "Parabens may disrupt hormones. Sulfates strip natural oils.",
        "suggestion": "Try WOW Onion Shampoo as a sulfate-free alternative.",
        "follow_up": "Want safer shampoo options?",
        "confidence": "high",
    },
    "nivea": {
        "type": "product_check",
        "verdict": "Safe",
        "summary": "Nivea Soft Cream has a mild formula with minimal concerns.",
        "key_ingredients": ["Mineral Oil"],
        "explanation": "Mineral oil is petroleum-derived but generally considered safe.",
        "suggestion": "Good choice for daily moisturizing.",
        "follow_up": "Want to check another product?",
        "confidence": "high",
    },
    "parachute": {
        "type": "product_check",
        "verdict": "Safe",
        "summary": "Parachute Coconut Oil is 100% pure coconut oil with no additives.",
        "key_ingredients": [],
        "explanation": "Single ingredient product - no concerns.",
        "suggestion": "Excellent choice for hair and skin.",
        "follow_up": "Want tips on using coconut oil?",
        "confidence": "high",
    },
    "colgate": {
        "type": "product_check",
        "verdict": "Use with caution",
        "summary": "Colgate Total contains triclosan which is a concern.",
        "key_ingredients": ["Triclosan", "Sodium Lauryl Sulfate"],
        "explanation": "Triclosan in toothpaste has been questioned for antimicrobial resistance.",
        "suggestion": "Consider triclosan-free toothpaste options.",
        "follow_up": "Want safer toothpaste recommendations?",
        "confidence": "high",
    },
    "lux": {
        "type": "product_check",
        "verdict": "Use with caution",
        "summary": "Lux Soft Touch Soap contains fragrance and BHT.",
        "key_ingredients": ["Fragrance", "BHT"],
        "explanation": "Fragrance can hide undisclosed chemicals.",
        "suggestion": "Try Pears Pure & Gentle for a cleaner option.",
        "follow_up": "Want safer options?",
        "confidence": "high",
    },
    "wow": {
        "type": "product_check",
        "verdict": "Safe",
        "summary": "WOW Onion Shampoo is a sulfate-free formula with natural ingredients.",
        "key_ingredients": ["Fragrance"],
        "explanation": "Uses natural fragrance blend, generally safe.",
        "suggestion": "Good sulfate-free choice.",
        "follow_up": "Want more hair care recommendations?",
        "confidence": "high",
    },
    "mamaearth": {
        "type": "product_check",
        "verdict": "Safe",
        "summary": "Mamaearth Vitamin C Face Wash uses natural ingredients.",
        "key_ingredients": ["Fragrance"],
        "explanation": "Contains natural fragrance, overall clean formula.",
        "suggestion": "Good option for most skin types.",
        "follow_up": "Want to check more products?",
        "confidence": "high",
    },
    "unknown_product": {
        "type": "product_check",
        "verdict": "Use with caution",
        "summary": "Cetaphil Gentle Cleanser appears generally safe but may contain fragrance.",
        "key_ingredients": ["Fragrance"],
        "explanation": "Without full ingredient verification, exercise caution.",
        "suggestion": "Send a photo of the full ingredient list for a better check.",
        "follow_up": "Want to send the ingredient list?",
        "confidence": "medium",
    },
    "image_product": {
        "type": "product_check",
        "verdict": "Use with caution",
        "summary": "Himalaya Neem Face Wash contains parabens and fragrance.",
        "key_ingredients": ["Methylparaben", "Fragrance"],
        "explanation": "Parabens are preservatives linked to endocrine disruption.",
        "suggestion": "Look for paraben-free alternatives.",
        "follow_up": "Want safer face wash options?",
        "confidence": "medium",
    },
    "hello": {
        "type": "general_advice",
        "verdict": None,
        "summary": "Hey, I'm Veda! Send me a product name to check if it's safe.",
        "key_ingredients": [],
        "explanation": "I help you check products for harmful ingredients.",
        "suggestion": "Try sending a product name like 'Dove soap' or a photo of a label.",
        "follow_up": "What product would you like to check?",
        "confidence": "high",
    },
    "tip": {
        "type": "habit_advice",
        "verdict": None,
        "summary": "Great question! Here are some tips for reducing chemical exposure.",
        "key_ingredients": [],
        "explanation": "Reducing chemical exposure starts with checking your daily products.",
        "suggestion": "Start by checking the products you use most often.",
        "follow_up": "Want to check a specific product?",
        "confidence": "high",
    },
    "default": {
        "type": "general_advice",
        "verdict": None,
        "summary": "I can help with health and product safety questions.",
        "key_ingredients": [],
        "explanation": None,
        "suggestion": None,
        "follow_up": "Want to check a product?",
        "confidence": "high",
    },
}


# ---------------------------------------------------------------------------
# MockResult - returned by .execute()
# ---------------------------------------------------------------------------
class MockResult:
    def __init__(self, data=None, count=None):
        self.data = data if data is not None else []
        self.count = count if count is not None else len(self.data)


# ---------------------------------------------------------------------------
# MockSupabase - in-memory Supabase client mock
# ---------------------------------------------------------------------------
class MockQueryBuilder:
    """Chainable query builder that mimics Supabase PostgREST client."""

    def __init__(self, db, table_name):
        self._db = db
        self._table_name = table_name
        self._operation = None  # "select", "insert", "update", "delete"
        self._select_columns = "*"
        self._count_mode = None
        self._filters = {}  # col -> value
        self._gte_filters = {}  # col -> value
        self._insert_data = None
        self._update_data = None
        self._order_col = None
        self._order_desc = False
        self._limit_val = None
        self._range_start = None
        self._range_end = None
        self._maybe_single = False

    # -- Operation starters --------------------------------------------------

    def select(self, columns="*", count=None):
        self._operation = "select"
        self._select_columns = columns
        self._count_mode = count
        return self

    def insert(self, data):
        self._operation = "insert"
        self._insert_data = data
        return self

    def update(self, data):
        self._operation = "update"
        self._update_data = data
        return self

    def delete(self):
        self._operation = "delete"
        return self

    # -- Filters -------------------------------------------------------------

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def gte(self, col, val):
        self._gte_filters[col] = val
        return self

    def limit(self, n):
        self._limit_val = n
        return self

    def order(self, col, desc=False):
        self._order_col = col
        self._order_desc = desc
        return self

    def range(self, start, end):
        self._range_start = start
        self._range_end = end
        return self

    def maybe_single(self):
        self._maybe_single = True
        return self

    # -- Execute -------------------------------------------------------------

    def _get_table_data(self):
        return self._db.tables.get(self._table_name, [])

    def _match(self, row):
        for col, val in self._filters.items():
            if row.get(col) != val:
                return False
        for col, val in self._gte_filters.items():
            row_val = row.get(col, "")
            if str(row_val) < str(val):
                return False
        return True

    def execute(self):
        if self._operation == "select":
            return self._exec_select()
        elif self._operation == "insert":
            return self._exec_insert()
        elif self._operation == "update":
            return self._exec_update()
        elif self._operation == "delete":
            return self._exec_delete()
        return MockResult()

    def _exec_select(self):
        rows = [dict(r) for r in self._get_table_data() if self._match(r)]

        # Simulate PostgREST join: "*, health_items(*)" on user_products table
        if (
            self._table_name == "user_products"
            and "health_items" in self._select_columns
        ):
            health_items = self._db.tables.get("health_items", [])
            for row in rows:
                hid = row.get("health_item_id")
                matched_item = None
                if hid:
                    for hi in health_items:
                        if hi.get("id") == hid:
                            matched_item = hi
                            break
                row["health_items"] = matched_item

        if self._order_col:
            rows = sorted(
                rows,
                key=lambda r: r.get(self._order_col, ""),
                reverse=self._order_desc,
            )

        total_count = len(rows)

        if self._range_start is not None and self._range_end is not None:
            rows = rows[self._range_start: self._range_end + 1]

        if self._limit_val is not None:
            rows = rows[: self._limit_val]

        if self._maybe_single:
            data = rows[0] if rows else None
            return MockResult(data=data, count=total_count if self._count_mode else None)

        return MockResult(
            data=rows,
            count=total_count if self._count_mode else len(rows),
        )

    def _exec_insert(self):
        table = self._db.tables.setdefault(self._table_name, [])
        data = self._insert_data
        if isinstance(data, dict):
            data = dict(data)  # copy
            if "id" not in data:
                data["id"] = str(uuid.uuid4())
            if "created_at" not in data:
                data["created_at"] = datetime.now(timezone.utc).isoformat()
            if self._table_name == "conversations" and "timestamp" not in data:
                data["timestamp"] = datetime.now(timezone.utc).isoformat()
            if self._table_name == "user_products":
                if "check_count" not in data:
                    data["check_count"] = 1
                if "last_checked_at" not in data:
                    data["last_checked_at"] = datetime.now(timezone.utc).isoformat()
            table.append(data)
            return MockResult(data=[data], count=1)
        elif isinstance(data, list):
            results = []
            for item in data:
                item = dict(item)
                if "id" not in item:
                    item["id"] = str(uuid.uuid4())
                table.append(item)
                results.append(item)
            return MockResult(data=results, count=len(results))
        return MockResult()

    def _exec_update(self):
        table = self._get_table_data()
        updated = []
        for row in table:
            if self._match(row):
                row.update(self._update_data)
                updated.append(row)
        return MockResult(data=updated, count=len(updated))

    def _exec_delete(self):
        table = self._get_table_data()
        to_remove = [r for r in table if self._match(r)]
        for r in to_remove:
            table.remove(r)
        return MockResult(data=to_remove, count=len(to_remove))


class MockRpcBuilder:
    """Handles supabase.rpc(...).execute() calls."""

    def __init__(self, db, func_name, params):
        self._db = db
        self._func_name = func_name
        self._params = params

    def execute(self):
        if self._func_name == "search_health_items":
            return self._search_health_items()
        return MockResult()

    def _search_health_items(self):
        query = (self._params.get("query") or "").lower()
        if not query:
            return MockResult(data=[])

        results = []
        for product in self._db.tables.get("health_items", []):
            item_name = product.get("item_name", "").lower()
            brand = product.get("brand", "").lower()
            aliases = product.get("aliases", [])
            alias_strs = [a.lower() for a in aliases] if aliases else []

            # Simple substring matching for fuzzy search
            matched = False
            score = 0.0

            if query in item_name or item_name in query:
                matched = True
                score = 0.9
            elif query in brand or brand in query:
                matched = True
                score = 0.7
            else:
                for alias in alias_strs:
                    if query in alias or alias in query:
                        matched = True
                        score = 0.8
                        break

            # Also check individual words
            if not matched:
                query_words = query.split()
                for word in query_words:
                    if len(word) < 3:
                        continue
                    if word in item_name or word in brand:
                        matched = True
                        score = 0.5
                        break
                    for alias in alias_strs:
                        if word in alias:
                            matched = True
                            score = 0.5
                            break

            if matched:
                result = dict(product)
                result["similarity_score"] = score
                results.append(result)

        # Sort by similarity descending
        results.sort(key=lambda r: r.get("similarity_score", 0), reverse=True)
        return MockResult(data=results)


class MockSupabase:
    """In-memory mock of supabase.Client with builder-pattern query support."""

    def __init__(self):
        self.tables = {
            "health_items": [dict(p) for p in TEST_PRODUCTS],
            "users": [],
            "conversations": [],
            "user_products": [],
            "unknown_queries": [],
            "feedback": [],
        }

    def table(self, name):
        return MockQueryBuilder(self, name)

    def rpc(self, func_name, params=None):
        return MockRpcBuilder(self, func_name, params or {})


# ---------------------------------------------------------------------------
# MockGemini - returns pre-configured responses based on keywords
# ---------------------------------------------------------------------------
class _MockUsageMetadata:
    def __init__(self):
        self.prompt_token_count = 100
        self.candidates_token_count = 200


class _MockGeminiResponse:
    def __init__(self, text):
        self._text = text
        self.usage_metadata = _MockUsageMetadata()

    @property
    def text(self):
        return self._text


class _MockAioModels:
    def __init__(self, gemini):
        self._gemini = gemini

    async def generate_content(self, model=None, contents=None, config=None):
        if self._gemini.timeout_mode:
            raise asyncio.TimeoutError("Simulated Gemini timeout")

        if self._gemini.fail_mode:
            raise Exception("Simulated Gemini API failure")

        # Extract the user's text message from contents
        user_text = ""
        if contents:
            for content in reversed(contents):
                role = getattr(content, "role", None)
                if role == "user":
                    parts = getattr(content, "parts", [])
                    for part in parts:
                        text = getattr(part, "text", None)
                        if text:
                            user_text = text
                            break
                    if user_text:
                        break

        # Determine response based on keywords
        user_lower = user_text.lower()
        response_data = None

        # Check for specific product keywords first
        keyword_order = [
            "dove", "pears", "dettol", "pantene", "nivea", "parachute",
            "colgate", "lux", "wow", "mamaearth",
        ]
        for kw in keyword_order:
            if kw in user_lower:
                response_data = GEMINI_RESPONSES[kw]
                break

        # Check for special keywords
        if response_data is None:
            if "hello" in user_lower or "hi" in user_lower or "hey" in user_lower:
                response_data = GEMINI_RESPONSES["hello"]
            elif "tip" in user_lower or "advice" in user_lower or "habit" in user_lower:
                response_data = GEMINI_RESPONSES["tip"]
            elif "image" in user_lower or "label" in user_lower or "product label" in user_lower:
                response_data = GEMINI_RESPONSES["image_product"]
            elif "cetaphil" in user_lower or "unknown" in user_lower:
                response_data = GEMINI_RESPONSES["unknown_product"]
            else:
                response_data = GEMINI_RESPONSES["default"]

        return _MockGeminiResponse(json.dumps(response_data))


class _MockAio:
    def __init__(self, gemini):
        self.models = _MockAioModels(gemini)


class MockGemini:
    """Mock of google.genai.Client with .aio.models.generate_content() support."""

    def __init__(self):
        self.timeout_mode = False
        self.fail_mode = False
        self.aio = _MockAio(self)


# ---------------------------------------------------------------------------
# MockWhatsApp - captures all outbound messages
# ---------------------------------------------------------------------------
class MockWhatsApp:
    def __init__(self, settings):
        self.settings = settings
        self.sent_messages = []  # list of (to, text) tuples
        self.sent_templates = []
        self.sent_buttons = []
        self.download_fail = False
        self.image_size = 1000  # bytes

    async def send_text_message(self, to, text):
        self.sent_messages.append((to, text))
        return {"messages": [{"id": "sent"}]}

    async def send_template_message(self, to, template_name, language="en"):
        self.sent_templates.append((to, template_name))
        return {}

    async def send_feedback_buttons(self, to, message_id):
        self.sent_buttons.append((to, message_id))
        return {}

    async def send_feedback_followup(self, to):
        return {}

    async def get_media_url(self, media_id):
        if self.download_fail:
            raise Exception("Media download failed")
        return "https://fake-cdn.com/media"

    async def download_media(self, url):
        if self.download_fail:
            raise Exception("Download failed")
        return b"\xff\xd8" * (self.image_size // 2)  # fake JPEG bytes

    def last_reply(self):
        return self.sent_messages[-1][1] if self.sent_messages else ""

    def clear(self):
        self.sent_messages.clear()
        self.sent_templates.clear()
        self.sent_buttons.clear()


# ---------------------------------------------------------------------------
# ConversationSimulator
# ---------------------------------------------------------------------------
_TEST_SYSTEM_PROMPT = (
    "You are Veda - a health coach chatbot. Respond in JSON format. "
    "Help users check products for harmful ingredients."
)


class ConversationSimulator:
    def __init__(self):
        self.settings = get_settings()
        self.mock_db = MockSupabase()
        self.mock_gemini = MockGemini()
        self.mock_whatsapp = MockWhatsApp(self.settings)
        self.user_phone = "+919999999999"
        self.msg_counter = 0

    async def send(self, text, message_type="text"):
        """Send a text message through the full pipeline."""
        from app.core.message_handler import handle_incoming_message
        from app.services.ai_engine import AIEngine

        self.msg_counter += 1
        message_id = f"wamid.sim{self.msg_counter}"

        ai_engine = AIEngine(
            client=self.mock_gemini,
            settings=self.settings,
            base_system_prompt=_TEST_SYSTEM_PROMPT,
        )

        await handle_incoming_message(
            whatsapp_number=self.user_phone,
            message_text=text,
            message_type=message_type,
            message_id=message_id,
            media_id=None,
            media_mime_type=None,
            supabase=self.mock_db,
            whatsapp_client=self.mock_whatsapp,
            ai_engine=ai_engine,
            settings=self.settings,
        )

    async def send_image(self, caption=None):
        """Send an image message through the full pipeline."""
        from app.core.message_handler import handle_incoming_message
        from app.services.ai_engine import AIEngine

        self.msg_counter += 1
        message_id = f"wamid.sim{self.msg_counter}"

        ai_engine = AIEngine(
            client=self.mock_gemini,
            settings=self.settings,
            base_system_prompt=_TEST_SYSTEM_PROMPT,
        )

        await handle_incoming_message(
            whatsapp_number=self.user_phone,
            message_text=caption,
            message_type="image",
            message_id=message_id,
            media_id="media_sim_123",
            media_mime_type="image/jpeg",
            supabase=self.mock_db,
            whatsapp_client=self.mock_whatsapp,
            ai_engine=ai_engine,
            settings=self.settings,
        )

    def last_reply(self):
        return self.mock_whatsapp.last_reply()

    def all_replies(self):
        return [text for _, text in self.mock_whatsapp.sent_messages]

    def reply_contains(self, *keywords):
        reply = self.last_reply().lower()
        return all(kw.lower() in reply for kw in keywords)

    def reply_not_contains(self, *keywords):
        reply = self.last_reply().lower()
        return all(kw.lower() not in reply for kw in keywords)

    def db_count(self, table):
        return len(self.mock_db.tables.get(table, []))

    def feedback_buttons_sent(self):
        return len(self.mock_whatsapp.sent_buttons) > 0

    def set_gemini_timeout(self):
        self.mock_gemini.timeout_mode = True

    def set_gemini_normal(self):
        self.mock_gemini.timeout_mode = False

    def set_gemini_fail(self):
        self.mock_gemini.fail_mode = True

    def set_gemini_normal_all(self):
        self.mock_gemini.timeout_mode = False
        self.mock_gemini.fail_mode = False

    def set_image_size(self, size_bytes):
        self.mock_whatsapp.image_size = size_bytes

    def set_download_fail(self):
        self.mock_whatsapp.download_fail = True

    def set_download_normal(self):
        self.mock_whatsapp.download_fail = False

    def get_user_products(self):
        user_id = self._get_user_id()
        if not user_id:
            return []
        return [
            p for p in self.mock_db.tables.get("user_products", [])
            if p.get("user_id") == user_id
        ]

    def _get_user_id(self):
        for user in self.mock_db.tables.get("users", []):
            if user.get("whatsapp_number") == self.user_phone:
                return user["id"]
        return None

    def get_conversations(self, role=None):
        user_id = self._get_user_id()
        if not user_id:
            return []
        convos = [
            c for c in self.mock_db.tables.get("conversations", [])
            if c.get("user_id") == user_id
        ]
        if role:
            convos = [c for c in convos if c.get("role") == role]
        return convos

    def clear_messages(self):
        self.mock_whatsapp.clear()
