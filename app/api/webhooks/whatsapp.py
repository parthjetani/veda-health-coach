import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Query, Request, Response

from app.config import get_settings
from app.core.feedback_handler import handle_feedback
from app.core.message_handler import handle_incoming_message
from app.models.whatsapp import WhatsAppWebhook, extract_message
from app.services.ai_engine import AIEngine
from app.services.whatsapp_client import WhatsAppClient, normalize_phone_number

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
) -> Response:
    settings = get_settings()

    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        logger.info("Webhook verified successfully")
        return Response(content=hub_challenge, media_type="text/plain")

    logger.warning("Webhook verification failed - token mismatch")
    return Response(content="Forbidden", status_code=403)


@router.post("")
async def receive_message(
    request: Request,
    background_tasks: BackgroundTasks,
):
    settings = get_settings()

    # Read raw body first (needed for signature verification)
    raw_body = await request.body()

    # Verify webhook signature if app_secret is configured
    if settings.whatsapp_app_secret:
        signature = request.headers.get("x-hub-signature-256", "")
        expected = "sha256=" + hmac.new(
            settings.whatsapp_app_secret.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            logger.warning("Invalid webhook signature - rejecting payload")
            return {"status": "ok"}  # silent reject

    # Parse the already-read body
    try:
        body = json.loads(raw_body)
        payload = WhatsAppWebhook(**body)
    except Exception as e:
        logger.error("Failed to parse WhatsApp webhook payload: %s", e)
        return {"status": "ok"}

    # Extract the first message (ignore status updates)
    message = extract_message(payload)
    if message is None:
        return {"status": "ok"}

    sender = normalize_phone_number(message.from_ or "")
    if not sender:
        return {"status": "ok"}

    whatsapp_client = WhatsAppClient(
        http_client=request.app.state.http_client,
        settings=settings,
    )

    # Handle interactive button replies (feedback)
    if message.type == "interactive" and message.interactive:
        button_id = message.interactive.button_reply.id if message.interactive.button_reply else ""
        background_tasks.add_task(
            handle_feedback,
            whatsapp_number=sender,
            button_id=button_id,
            supabase=request.app.state.supabase,
            whatsapp_client=whatsapp_client,
        )
        return {"status": "ok"}

    # Only handle text and image messages
    if message.type not in ("text", "image"):
        logger.debug("Ignoring unsupported message type: %s", message.type)
        return {"status": "ok"}

    message_text = None
    media_id = None
    media_mime_type = None

    if message.type == "text" and message.text:
        message_text = message.text.body
    elif message.type == "image" and message.image:
        media_id = message.image.id
        media_mime_type = message.image.mime_type
        message_text = message.image.caption

    ai_engine = AIEngine(
        client=request.app.state.gemini_client,
        settings=settings,
        base_system_prompt=request.app.state.system_prompt,
    )

    # Process in background
    background_tasks.add_task(
        handle_incoming_message,
        whatsapp_number=sender,
        message_text=message_text,
        message_type=message.type,
        message_id=message.id,
        media_id=media_id,
        media_mime_type=media_mime_type,
        supabase=request.app.state.supabase,
        whatsapp_client=whatsapp_client,
        ai_engine=ai_engine,
        settings=settings,
    )

    return {"status": "ok"}
