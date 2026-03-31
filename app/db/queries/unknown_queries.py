import logging

from supabase import Client

logger = logging.getLogger(__name__)


async def log_unknown_query(
    supabase: Client,
    user_id: str,
    query_text: str,
) -> dict | None:
    result = (
        supabase.table("unknown_queries")
        .insert({"user_id": user_id, "query_text": query_text})
        .execute()
    )
    logger.info("Logged unknown query: %s", query_text[:80])
    return result.data[0] if result.data else None


async def list_unknown_queries(
    supabase: Client,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[dict], int]:
    offset = (page - 1) * per_page

    count_result = (
        supabase.table("unknown_queries")
        .select("id", count="exact")
        .execute()
    )
    total = count_result.count or 0

    result = (
        supabase.table("unknown_queries")
        .select("*")
        .order("timestamp", desc=True)
        .range(offset, offset + per_page - 1)
        .execute()
    )
    return result.data or [], total
