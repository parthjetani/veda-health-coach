import logging

from supabase import Client

from app.db.queries.feedback import store_feedback
from app.db.queries.users import get_user_by_whatsapp
from app.services.conversation import get_conversation_history
from app.services.whatsapp_client import WhatsAppClient

logger = logging.getLogger(__name__)


async def handle_feedback(
    whatsapp_number: str,
    button_id: str,
    supabase: Client,
    whatsapp_client: WhatsAppClient,
) -> None:
    try:
        user = await get_user_by_whatsapp(supabase, whatsapp_number)
        if not user:
            return

        user_id = user["id"]

        # Parse button_id: "feedback_good_{msg_id}", "feedback_bad_{msg_id}",
        # "feedback_incorrect", "feedback_generic", "feedback_other"
        if button_id.startswith("feedback_good_"):
            msg_id = button_id.replace("feedback_good_", "")
            user_query, ai_response = await _get_last_exchange(supabase, user_id)
            await store_feedback(
                supabase, user_id, msg_id, "good",
                user_query=user_query, ai_response=ai_response,
            )
            await whatsapp_client.send_text_message(
                whatsapp_number, "Thanks! Glad that was helpful."
            )

        elif button_id.startswith("feedback_bad_"):
            msg_id = button_id.replace("feedback_bad_", "")
            user_query, ai_response = await _get_last_exchange(supabase, user_id)
            await store_feedback(
                supabase, user_id, msg_id, "bad",
                user_query=user_query, ai_response=ai_response,
            )
            # Ask follow-up reason
            await whatsapp_client.send_feedback_followup(whatsapp_number)

        elif button_id in ("feedback_incorrect", "feedback_generic", "feedback_other"):
            reason = button_id.replace("feedback_", "")
            # Update the most recent bad feedback with the reason
            result = (
                supabase.table("feedback")
                .select("id")
                .eq("user_id", user_id)
                .eq("rating", "bad")
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            if result.data:
                supabase.table("feedback").update(
                    {"reason": reason}
                ).eq("id", result.data[0]["id"]).execute()

            await whatsapp_client.send_text_message(
                whatsapp_number, "Got it, thanks for the feedback. I'll work on getting better!"
            )

        logger.info("Feedback processed: %s from %s", button_id, whatsapp_number)

    except Exception as e:
        logger.exception("Error handling feedback from %s: %s", whatsapp_number, e)


async def _get_last_exchange(supabase: Client, user_id: str) -> tuple[str | None, str | None]:
    history = await get_conversation_history(supabase, user_id, limit=2)
    user_query = None
    ai_response = None
    for msg in history:
        if msg.get("role") == "user":
            user_query = msg.get("message_text")
        elif msg.get("role") == "assistant":
            ai_response = msg.get("message_text")
    return user_query, ai_response
