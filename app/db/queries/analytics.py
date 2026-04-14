import asyncio
import logging

from supabase import Client

logger = logging.getLogger(__name__)


async def get_analytics(supabase: Client) -> dict:
    # Supabase Python client is synchronous. Run all independent queries
    # concurrently via asyncio.to_thread so wall time is max() not sum().
    def q_total_users():
        return supabase.table("users").select("id", count="exact").execute()

    def q_total_messages():
        return supabase.table("conversations").select("id", count="exact").execute()

    def q_user_messages():
        return (
            supabase.table("conversations")
            .select("id", count="exact")
            .eq("role", "user")
            .execute()
        )

    def q_kb_matches():
        return (
            supabase.table("conversations")
            .select("id", count="exact")
            .eq("role", "assistant")
            .contains("metadata", {"kb_match": True})
            .execute()
        )

    def q_kb_misses():
        return (
            supabase.table("conversations")
            .select("id", count="exact")
            .eq("role", "assistant")
            .contains("metadata", {"kb_match": False})
            .execute()
        )

    def q_good_feedback():
        return (
            supabase.table("feedback")
            .select("id", count="exact")
            .eq("rating", "good")
            .execute()
        )

    def q_bad_feedback():
        return (
            supabase.table("feedback")
            .select("id", count="exact")
            .eq("rating", "bad")
            .execute()
        )

    def q_unresolved_queries():
        return (
            supabase.table("unknown_queries")
            .select("id", count="exact")
            .eq("resolved", False)
            .execute()
        )

    def q_total_products():
        return supabase.table("health_items").select("id", count="exact").execute()

    def q_top_unknown():
        return (
            supabase.table("unknown_queries")
            .select("query_text")
            .eq("resolved", False)
            .order("timestamp", desc=True)
            .limit(10)
            .execute()
        )

    def q_bad_reasons():
        return (
            supabase.table("feedback")
            .select("reason")
            .eq("rating", "bad")
            .not_.is_("reason", "null")
            .order("timestamp", desc=True)
            .limit(10)
            .execute()
        )

    (
        users_result,
        messages_result,
        user_messages_result,
        matched_result,
        unmatched_result,
        good_feedback,
        bad_feedback,
        unknown_result,
        products_result,
        top_unknown,
        bad_reasons,
    ) = await asyncio.gather(
        asyncio.to_thread(q_total_users),
        asyncio.to_thread(q_total_messages),
        asyncio.to_thread(q_user_messages),
        asyncio.to_thread(q_kb_matches),
        asyncio.to_thread(q_kb_misses),
        asyncio.to_thread(q_good_feedback),
        asyncio.to_thread(q_bad_feedback),
        asyncio.to_thread(q_unresolved_queries),
        asyncio.to_thread(q_total_products),
        asyncio.to_thread(q_top_unknown),
        asyncio.to_thread(q_bad_reasons),
    )

    total_users = users_result.count or 0
    total_messages = messages_result.count or 0
    user_messages = user_messages_result.count or 0
    kb_matches = matched_result.count or 0
    kb_misses = unmatched_result.count or 0
    kb_total = kb_matches + kb_misses
    kb_match_rate = round((kb_matches / kb_total * 100), 1) if kb_total > 0 else 0
    good_count = good_feedback.count or 0
    bad_count = bad_feedback.count or 0
    total_feedback = good_count + bad_count
    satisfaction_rate = round((good_count / total_feedback * 100), 1) if total_feedback > 0 else 0
    unresolved_queries = unknown_result.count or 0
    total_products = products_result.count or 0

    return {
        "overview": {
            "total_users": total_users,
            "total_messages": total_messages,
            "user_messages": user_messages,
            "total_products_in_kb": total_products,
        },
        "quality": {
            "kb_match_rate": f"{kb_match_rate}%",
            "kb_matches": kb_matches,
            "kb_misses": kb_misses,
            "satisfaction_rate": f"{satisfaction_rate}%",
            "good_feedback": good_count,
            "bad_feedback": bad_count,
        },
        "action_needed": {
            "unresolved_unknown_queries": unresolved_queries,
            "top_unknown_queries": [q["query_text"] for q in (top_unknown.data or [])],
            "recent_bad_feedback_reasons": [r["reason"] for r in (bad_reasons.data or [])],
        },
    }
