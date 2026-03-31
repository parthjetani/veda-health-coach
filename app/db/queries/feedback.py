import logging

from supabase import Client

logger = logging.getLogger(__name__)


async def store_feedback(
    supabase: Client,
    user_id: str,
    message_id: str | None,
    rating: str,
    reason: str | None = None,
    user_query: str | None = None,
    ai_response: str | None = None,
) -> dict | None:
    data = {
        "user_id": user_id,
        "message_id": message_id,
        "rating": rating,
    }
    if reason:
        data["reason"] = reason
    if user_query:
        data["user_query"] = user_query
    if ai_response:
        data["ai_response"] = ai_response

    result = supabase.table("feedback").insert(data).execute()
    logger.info("Feedback stored: %s (reason: %s)", rating, reason)
    return result.data[0] if result.data else None


async def list_feedback(
    supabase: Client,
    rating: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[dict], int]:
    offset = (page - 1) * per_page

    query = supabase.table("feedback").select("*", count="exact")
    if rating:
        query = query.eq("rating", rating)
    count_result = query.execute()
    total = count_result.count or 0

    query = supabase.table("feedback").select("*")
    if rating:
        query = query.eq("rating", rating)
    result = query.order("timestamp", desc=True).range(offset, offset + per_page - 1).execute()

    return result.data or [], total
