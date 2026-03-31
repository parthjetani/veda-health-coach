from supabase import Client

from app.db.queries.conversations import (
    check_message_exists,
    get_last_n_messages,
    insert_message,
)


async def store_message(
    supabase: Client,
    user_id: str,
    role: str,
    text: str,
    whatsapp_msg_id: str | None = None,
    metadata: dict | None = None,
) -> dict | None:
    return await insert_message(supabase, user_id, role, text, whatsapp_msg_id, metadata)


async def get_conversation_history(
    supabase: Client,
    user_id: str,
    limit: int = 15,
) -> list[dict]:
    return await get_last_n_messages(supabase, user_id, limit)


async def is_duplicate_message(supabase: Client, whatsapp_msg_id: str) -> bool:
    if not whatsapp_msg_id:
        return False
    return await check_message_exists(supabase, whatsapp_msg_id)
