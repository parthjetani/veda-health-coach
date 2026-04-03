import html
import logging

from supabase import Client

logger = logging.getLogger(__name__)


async def search_health_items(
    supabase: Client,
    query: str,
    threshold: float = 0.3,
) -> list[dict]:
    result = supabase.rpc(
        "search_health_items",
        {"query": query, "match_threshold": threshold},
    ).execute()
    return result.data or []


async def list_health_items(
    supabase: Client,
    page: int = 1,
    per_page: int = 20,
    category: str | None = None,
    risk_level: str | None = None,
    confidence_source: str | None = None,
) -> tuple[list[dict], int]:
    offset = (page - 1) * per_page

    # Single query with count + pagination (was previously two queries)
    query = supabase.table("health_items").select("*", count="exact")
    if category:
        query = query.eq("category", category)
    if risk_level:
        query = query.eq("risk_level", risk_level)
    if confidence_source:
        query = query.eq("confidence_source", confidence_source)

    result = query.order("item_name").range(offset, offset + per_page - 1).execute()
    return result.data or [], result.count or 0


async def get_health_item(supabase: Client, item_id: str) -> dict | None:
    result = (
        supabase.table("health_items")
        .select("*")
        .eq("id", item_id)
        .maybe_single()
        .execute()
    )
    return result.data


async def create_health_item(supabase: Client, data: dict) -> dict:
    result = (
        supabase.table("health_items")
        .insert(data)
        .execute()
    )
    logger.info("Created health item: %s", data.get("item_name"))
    return result.data[0]


async def update_health_item(supabase: Client, item_id: str, data: dict) -> dict | None:
    result = (
        supabase.table("health_items")
        .update(data)
        .eq("id", item_id)
        .execute()
    )
    if result.data:
        logger.info("Updated health item: %s", item_id)
        return result.data[0]
    return None


async def delete_health_item(supabase: Client, item_id: str) -> bool:
    result = (
        supabase.table("health_items")
        .delete()
        .eq("id", item_id)
        .execute()
    )
    if result.data:
        logger.info("Deleted health item: %s", item_id)
        return True
    return False


_VERDICT_TO_RISK = {"Safe": "low", "Use with caution": "medium", "Avoid": "high"}


async def auto_insert_inferred_product(
    supabase: Client,
    product_name: str,
    verdict: str | None,
    key_ingredients: list[str] | None,
) -> dict | None:
    # Guardrails: skip noisy/low-quality data
    if not product_name or len(product_name.strip()) < 5:
        return None
    if not verdict:
        return None
    if not key_ingredients or len(key_ingredients) < 1:
        return None

    product_name = html.escape(product_name.strip())  # sanitize for XSS prevention

    # Reject generic/junk names
    _blocklist = {"product label image", "check this", "is this safe", "hello", "hi",
                  "thanks", "yes", "no", "ok", "sure", "please", "soap", "cream", "shampoo"}
    if product_name.lower() in _blocklist:
        return None
    if len(product_name.split()) < 2:
        return None

    # Check if product already exists (exact match)
    existing = (
        supabase.table("health_items")
        .select("id")
        .eq("item_name", product_name)
        .limit(1)
        .execute()
    )
    if existing.data:
        return None

    # Also check fuzzy match to avoid near-duplicates
    fuzzy_results = await search_health_items(supabase, product_name, threshold=0.5)
    if fuzzy_results:
        logger.debug("Skipping inferred insert - fuzzy match found: %s -> %s",
                      product_name, fuzzy_results[0].get("item_name"))
        return None

    # Build structured flagged ingredients from AI response
    flagged = []
    for name in (key_ingredients or []):
        flagged.append({"name": name})

    data = {
        "item_name": product_name,
        "flagged_ingredients": flagged,
        "risk_level": _VERDICT_TO_RISK.get(verdict, "medium"),
        "confidence_source": "inferred",
    }

    try:
        result = supabase.table("health_items").insert(data).execute()
        logger.info("Auto-inserted inferred product: %s (risk: %s)", product_name, data["risk_level"])
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error("Failed to auto-insert inferred product %s: %s", product_name, e)
        return None
