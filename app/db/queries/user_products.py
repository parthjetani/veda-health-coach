import logging
from datetime import datetime, timezone

from supabase import Client

logger = logging.getLogger(__name__)


async def upsert_user_product(
    supabase: Client,
    user_id: str,
    product_name: str,
    health_item_id: str | None,
    score: int | None,
    confidence_source: str = "verified",
) -> dict | None:
    # Check if user already checked this product
    query = (
        supabase.table("user_products")
        .select("id, check_count")
        .eq("user_id", user_id)
        .eq("product_name", product_name)
        .limit(1)
        .execute()
    )

    existing = query.data[0] if query.data else None

    if existing:
        # Update: increment check_count, refresh last_checked_at and score
        result = (
            supabase.table("user_products")
            .update({
                "check_count": existing["check_count"] + 1,
                "last_checked_at": datetime.now(timezone.utc).isoformat(),
                "score": score,
            })
            .eq("id", existing["id"])
            .execute()
        )
        logger.debug("Updated user_product: %s (check #%d)", product_name, existing["check_count"] + 1)
        return result.data[0] if result.data else None
    else:
        # Insert new
        data = {
            "user_id": user_id,
            "product_name": product_name,
            "score": score,
            "confidence_source": confidence_source,
        }
        if health_item_id:
            data["health_item_id"] = health_item_id

        result = supabase.table("user_products").insert(data).execute()
        logger.info("Saved user_product: %s (score: %s)", product_name, score)
        return result.data[0] if result.data else None


async def get_user_products(supabase: Client, user_id: str) -> list[dict]:
    result = (
        supabase.table("user_products")
        .select("*")
        .eq("user_id", user_id)
        .order("last_checked_at", desc=True)
        .execute()
    )
    return result.data or []


async def get_user_products_with_items(supabase: Client, user_id: str) -> list[dict]:
    """Get user products with full health_items data (for footprint analysis)."""
    result = (
        supabase.table("user_products")
        .select("*, health_items(*)")
        .eq("user_id", user_id)
        .order("last_checked_at", desc=True)
        .execute()
    )
    return result.data or []


async def get_user_product_count(supabase: Client, user_id: str) -> int:
    result = (
        supabase.table("user_products")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    return result.count or 0
