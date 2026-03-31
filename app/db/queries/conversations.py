import logging

from supabase import Client

logger = logging.getLogger(__name__)


async def insert_message(
    supabase: Client,
    user_id: str,
    role: str,
    message_text: str,
    whatsapp_msg_id: str | None = None,
    metadata: dict | None = None,
) -> dict | None:
    data = {
        "user_id": user_id,
        "role": role,
        "message_text": message_text,
    }
    if whatsapp_msg_id:
        data["whatsapp_msg_id"] = whatsapp_msg_id
    if metadata:
        data["metadata"] = metadata

    try:
        result = supabase.table("conversations").insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        # If whatsapp_msg_id already exists (duplicate webhook), skip silently
        if "duplicate key" in str(e).lower() or "unique" in str(e).lower():
            logger.debug("Duplicate message skipped: %s", whatsapp_msg_id)
            return None
        raise


async def get_last_n_messages(
    supabase: Client,
    user_id: str,
    n: int = 15,
) -> list[dict]:
    result = (
        supabase.table("conversations")
        .select("role, message_text")
        .eq("user_id", user_id)
        .order("timestamp", desc=True)
        .limit(n)
        .execute()
    )
    # Reverse so oldest messages come first (AI expects chronological order)
    messages = result.data or []
    messages.reverse()
    return messages


async def check_message_exists(supabase: Client, whatsapp_msg_id: str) -> bool:
    result = (
        supabase.table("conversations")
        .select("id")
        .eq("whatsapp_msg_id", whatsapp_msg_id)
        .limit(1)
        .execute()
    )
    return len(result.data or []) > 0
