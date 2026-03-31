import logging

from supabase import Client

logger = logging.getLogger(__name__)


async def get_analytics(supabase: Client) -> dict:
    # Total users
    users_result = supabase.table("users").select("id", count="exact").execute()
    total_users = users_result.count or 0

    # Active users (sent at least one message)
    active_result = (
        supabase.table("conversations")
        .select("user_id", count="exact")
        .eq("role", "user")
        .execute()
    )

    # Total messages
    messages_result = supabase.table("conversations").select("id", count="exact").execute()
    total_messages = messages_result.count or 0

    # User messages only
    user_messages_result = (
        supabase.table("conversations")
        .select("id", count="exact")
        .eq("role", "user")
        .execute()
    )
    user_messages = user_messages_result.count or 0

    # KB match rate from metadata
    matched_result = (
        supabase.table("conversations")
        .select("id", count="exact")
        .eq("role", "assistant")
        .contains("metadata", {"kb_match": True})
        .execute()
    )
    kb_matches = matched_result.count or 0

    unmatched_result = (
        supabase.table("conversations")
        .select("id", count="exact")
        .eq("role", "assistant")
        .contains("metadata", {"kb_match": False})
        .execute()
    )
    kb_misses = unmatched_result.count or 0

    kb_total = kb_matches + kb_misses
    kb_match_rate = round((kb_matches / kb_total * 100), 1) if kb_total > 0 else 0

    # Feedback stats
    good_feedback = (
        supabase.table("feedback")
        .select("id", count="exact")
        .eq("rating", "good")
        .execute()
    )
    bad_feedback = (
        supabase.table("feedback")
        .select("id", count="exact")
        .eq("rating", "bad")
        .execute()
    )
    good_count = good_feedback.count or 0
    bad_count = bad_feedback.count or 0
    total_feedback = good_count + bad_count
    satisfaction_rate = round((good_count / total_feedback * 100), 1) if total_feedback > 0 else 0

    # Unknown queries count
    unknown_result = (
        supabase.table("unknown_queries")
        .select("id", count="exact")
        .eq("resolved", False)
        .execute()
    )
    unresolved_queries = unknown_result.count or 0

    # Product count
    products_result = supabase.table("health_items").select("id", count="exact").execute()
    total_products = products_result.count or 0

    # Top unknown queries (most asked products not in DB)
    top_unknown = (
        supabase.table("unknown_queries")
        .select("query_text")
        .eq("resolved", False)
        .order("timestamp", desc=True)
        .limit(10)
        .execute()
    )

    # Bad feedback reasons
    bad_reasons = (
        supabase.table("feedback")
        .select("reason")
        .eq("rating", "bad")
        .not_.is_("reason", "null")
        .order("timestamp", desc=True)
        .limit(10)
        .execute()
    )

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
