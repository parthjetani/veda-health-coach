import base64
import html
import json
import logging
import random
import re
from datetime import datetime, timedelta
from pathlib import Path

from supabase import Client

TEST_LOG_FILE = Path("test_conversations.txt")

from app.config import Settings
from app.core.errors import (
    GeminiTimeoutError,
    ImageDownloadError,
    ImageTooLargeError,
    RateLimitError,
    WhatsApp24hWindowError,
)
from app.core.footprint import format_footprint_message, get_progress, get_user_footprint
from app.core.product_comparison import compare_products, extract_comparison_products, is_compare_command
from app.core.product_scorer import calculate_score, format_score_breakdown
from app.core.response_formatter import parse_and_format
from app.db.queries.health_items import auto_insert_inferred_product
from app.db.queries.unknown_queries import log_unknown_query
from app.db.queries.user_products import get_user_product_count, upsert_user_product
from app.db.queries.users import get_or_create_user, update_last_active
from app.services.ai_engine import AIEngine
from app.services.conversation import (
    get_conversation_history,
    is_duplicate_message,
    store_message,
)
from app.services.knowledge_base import (
    build_swap_context,
    format_product_context,
    lookup_alternatives,
    lookup_product,
)
from app.services.source_context import build_source_context
from app.services.whatsapp_client import WhatsAppClient

logger = logging.getLogger(__name__)

_AFFIRMATIVES = {
    "yes", "yeah", "yep", "sure", "please", "ok", "okay",
    "go ahead", "tell me", "show me", "recommend", "alternatives",
}

_FOOTPRINT_KEYWORDS = {
    "footprint", "my products", "what have i checked", "my score",
    "my chemical exposure", "my overview", "show my products", "my history",
}

_SWAP_KEYWORDS = {
    "swap priority", "what should i swap", "what to replace",
    "what should i change", "help me swap", "what to swap",
    "swap first", "replace first",
}


def _is_affirmation(text: str) -> bool:
    return text.strip().lower().rstrip("!.,") in _AFFIRMATIVES


def _is_footprint_command(text: str) -> bool:
    return any(kw in text.strip().lower() for kw in _FOOTPRINT_KEYWORDS)


def _is_swap_command(text: str) -> bool:
    return any(kw in text.strip().lower() for kw in _SWAP_KEYWORDS)

# Contextual error messages
ERROR_MESSAGES = {
    ImageTooLargeError: "That image is too large. Please try a smaller or clearer photo.",
    ImageDownloadError: "I couldn't read that image. Could you try sending it again with better lighting?",
    GeminiTimeoutError: None,  # handled by fallback tips
    RateLimitError: "You're sending messages too quickly. Take a breather and try again in a few minutes.",
}
DEFAULT_ERROR = "Sorry, something went wrong. Please try again in a moment."

# Fallback health tips when AI is unavailable
FALLBACK_TIPS = [
    "Quick tip: Check your daily products for 'fragrance' - it can hide 50+ undisclosed chemicals.",
    "Did you know? Sulfate-free shampoos are gentler on your scalp and hair.",
    "Tip: 'Natural' on a label doesn't mean safe. Always check the full ingredient list.",
    "Quick check: If a product lists 'parfum' or 'perfume', it's synthetic fragrance.",
    "Tip: Parabens are preservatives that may affect hormone balance. Look for 'paraben-free' options.",
    "Did you know? The fewer ingredients a product has, the less likely it is to cause irritation.",
    "Quick tip: Store food in glass or steel containers instead of plastic to reduce chemical exposure.",
    "Tip: Mineral sunscreens (zinc oxide) are safer than chemical sunscreens (oxybenzone).",
    "Did you know? Most mosquito coils release chemicals equivalent to 100 cigarettes. Use nets instead.",
    "Quick tip: Choose unscented products over 'fragrance-free' - they mean different things.",
]


async def handle_incoming_message(
    whatsapp_number: str,
    message_text: str | None,
    message_type: str,
    message_id: str | None,
    media_id: str | None,
    media_mime_type: str | None,
    supabase: Client,
    whatsapp_client: WhatsAppClient,
    ai_engine: AIEngine,
    settings: Settings,
) -> None:
    try:
        await _process_message(
            whatsapp_number=whatsapp_number,
            message_text=message_text,
            message_type=message_type,
            message_id=message_id,
            media_id=media_id,
            media_mime_type=media_mime_type,
            supabase=supabase,
            whatsapp_client=whatsapp_client,
            ai_engine=ai_engine,
            settings=settings,
        )
    except GeminiTimeoutError as e:
        logger.error("[MSG] Gemini timeout: user=%s, msg_id=%s, error=%s", whatsapp_number, message_id, e)
        tip = random.choice(FALLBACK_TIPS)
        try:
            await whatsapp_client.send_text_message(
                whatsapp_number, f"{tip}\n\n(I had trouble analyzing your question - please try again.)"
            )
        except Exception:
            logger.exception("Failed to send fallback tip to %s", whatsapp_number)
    except (ImageTooLargeError, ImageDownloadError, RateLimitError) as e:
        logger.warning("[MSG] Handled error: user=%s, msg_id=%s, error=%s", whatsapp_number, message_id, e)
        msg = ERROR_MESSAGES.get(type(e), DEFAULT_ERROR)
        try:
            await whatsapp_client.send_text_message(whatsapp_number, msg)
        except Exception:
            logger.exception("Failed to send error message to %s", whatsapp_number)
    except Exception as e:
        logger.exception("[MSG] Unhandled error: user=%s, msg_id=%s, error=%s", whatsapp_number, message_id, e)
        try:
            await whatsapp_client.send_text_message(whatsapp_number, DEFAULT_ERROR)
        except Exception:
            logger.exception("Failed to send error message to %s", whatsapp_number)


async def _process_message(
    whatsapp_number: str,
    message_text: str | None,
    message_type: str,
    message_id: str | None,
    media_id: str | None,
    media_mime_type: str | None,
    supabase: Client,
    whatsapp_client: WhatsAppClient,
    ai_engine: AIEngine,
    settings: Settings,
) -> None:
    # Correlation logging — trace every message through the pipeline
    logger.info("[MSG] Start: user=%s, msg_id=%s, type=%s", whatsapp_number, message_id, message_type)

    # Step 1: Idempotency check
    if message_id and await is_duplicate_message(supabase, message_id):
        logger.debug("[MSG] Duplicate skipped: msg_id=%s", message_id)
        return

    # Step 2: Get or create user
    user = await get_or_create_user(supabase, whatsapp_number)
    user_id = user["id"]

    # Step 2.1: Track user activity (for 24h window)
    await update_last_active(supabase, user_id)

    # Step 2.5: Rate limiting
    if await _is_rate_limited(supabase, user_id, settings.rate_limit_per_hour):
        raise RateLimitError(f"User {whatsapp_number} exceeded {settings.rate_limit_per_hour} messages/hour")

    # Step 3: Download image if present
    image_b64 = None
    image_mime = None
    if message_type == "image" and media_id:
        try:
            media_url = await whatsapp_client.get_media_url(media_id)
            media_bytes = await whatsapp_client.download_media(media_url)
            # Reject oversized images
            if len(media_bytes) > settings.max_image_size_bytes:
                raise ImageTooLargeError(
                    f"Image size {len(media_bytes)} exceeds limit {settings.max_image_size_bytes}"
                )
            image_b64 = base64.b64encode(media_bytes).decode("utf-8")
            image_mime = media_mime_type or "image/jpeg"
        except ImageTooLargeError:
            raise  # Re-raise to be caught by handle_incoming_message
        except Exception as e:
            raise ImageDownloadError(f"Failed to download media {media_id}: {e}")

    # Step 4: Conversation history (fetched early for affirmation detection)
    history = await get_conversation_history(supabase, user_id, limit=10)

    query_text = message_text or "product label image"

    # Step 4.5: Special command routing (bypass AI for system-computed responses)
    if message_type == "text" and message_text:
        handled = await _handle_special_command(
            query_text, user_id, whatsapp_number, supabase, whatsapp_client, message_id
        )
        if handled:
            return

    # Step 5: Knowledge base lookup (skip for very short queries — prevents "Hi" matching "Himalaya")
    product_context = None
    source_context_str = ""
    if len(query_text.strip()) >= 4:
        kb_result = await lookup_product(supabase, query_text)
    else:
        kb_result = None

    product_score = None
    progress = None
    if kb_result:
        product_context = format_product_context(kb_result)
        flagged = kb_result.get("flagged_ingredients", [])
        if flagged:
            source_context_str = build_source_context(flagged)
        # Calculate product score
        product_score = calculate_score(kb_result)
        score_breakdown = format_score_breakdown(kb_result)
        product_context += f"\n\n{score_breakdown}"
        # Build Before/After swap comparison if alternative exists
        swap_context = await build_swap_context(supabase, kb_result)
        if swap_context:
            product_context += f"\n\n{swap_context}"
        # Auto-save to user product history
        await upsert_user_product(
            supabase, user_id, kb_result["item_name"],
            kb_result.get("id"), product_score, "verified"
        )
        # Calculate progress for this user
        progress = await get_progress(supabase, user_id)
        # Auto-nudge footprint after 3 products
        product_count = await get_user_product_count(supabase, user_id)
        if product_count == 3 and progress:
            progress["nudge"] = "You've checked 3 products! Type 'my footprint' to see your chemical exposure summary."
    elif _is_affirmation(query_text):
        alt_context = await lookup_alternatives(supabase, history)
        if alt_context:
            product_context = alt_context
            logger.info("Affirmation detected - injecting alternatives context")
        else:
            # No specific alternatives found, but user said "yes" to something.
            # Add context hint so Gemini knows to deliver on its previous offer.
            product_context = (
                "FOLLOW-UP CONTEXT: The user is responding affirmatively to your previous message. "
                "Check your conversation history and deliver what you offered or asked about. "
                "Do NOT ask them to clarify. Give them the information or recommendations directly."
            )
            logger.info("Affirmation detected - no alternatives, injecting follow-up hint")
    else:
        await log_unknown_query(supabase, user_id, query_text)

    # Step 7: Store user message
    await store_message(supabase, user_id, "user", query_text, message_id)

    # Step 8: Call AI engine
    raw_response = await ai_engine.get_response(
        user_message=query_text,
        conversation_history=history,
        product_context=product_context,
        source_context=source_context_str or None,
        image_base64=image_b64,
        image_mime_type=image_mime,
    )

    # Step 9: Format response (with score and progress if KB matched)
    reply_text = parse_and_format(raw_response, product_score=product_score, progress=progress)

    # Step 9.5: Log Q&A to test file (dev only)
    if not settings.is_production:
        _log_conversation(query_text, raw_response, reply_text, bool(kb_result))

    # Step 9.6: Save inferred product (unknown products analyzed by AI)
    if not kb_result:
        _parsed = _try_parse_response(raw_response)
        if _parsed and _parsed.get("type") == "product_check" and _parsed.get("verdict"):
            # Extract real product name (don't store "product label image")
            save_name = query_text
            if query_text == "product label image":
                extracted = _extract_product_name(_parsed)
                if extracted:
                    save_name = extracted
                else:
                    save_name = None  # skip saving garbage

            if save_name:
                inferred_score = _verdict_to_score(_parsed["verdict"])
                await upsert_user_product(
                    supabase, user_id, save_name, None, inferred_score, "inferred"
                )
                await auto_insert_inferred_product(
                    supabase, save_name,
                    _parsed.get("verdict"),
                    _parsed.get("key_ingredients"),
                )

    # Step 9.7: Build metadata for analytics
    metadata = _extract_metadata(raw_response, bool(kb_result))
    if product_score is not None:
        metadata["product_score"] = product_score
    metadata["raw_response"] = raw_response  # full JSON for debugging

    # Step 10: Store clean summary as conversation history (NOT formatted WhatsApp text)
    # Prepend verdict tag (e.g. "[Use with caution]") so lookup_alternatives can
    # still match the turn as a product check — the structured verdict field is
    # otherwise lost when we drop the emoji/score formatting from history.
    _parsed_for_history = _try_parse_response(raw_response)
    if _parsed_for_history:
        verdict = _parsed_for_history.get("verdict")
        summary = _parsed_for_history.get("summary", "")
        suggestion = _parsed_for_history.get("suggestion")
        clean_summary = f"[{verdict}] {summary}" if verdict else summary
        if suggestion:
            clean_summary += " " + suggestion
    else:
        clean_summary = reply_text  # fallback if parse failed

    await store_message(supabase, user_id, "assistant", clean_summary, metadata=metadata)

    # Step 11: Send reply (with 24h window fallback)
    try:
        await whatsapp_client.send_text_message(whatsapp_number, reply_text)
    except WhatsApp24hWindowError:
        logger.warning("24h window expired for %s, sending template", whatsapp_number)
        await whatsapp_client.send_template_message(whatsapp_number, "how_to_use")
        return

    # Step 12: Send feedback buttons
    await whatsapp_client.send_feedback_buttons(
        whatsapp_number, message_id or "unknown"
    )

    logger.info(
        "[MSG] Done: user=%s, msg_id=%s, type=%s, kb_match=%s, score=%s",
        whatsapp_number, message_id, message_type, bool(kb_result), product_score,
    )


def _log_conversation(
    question: str,
    raw_json: str,
    formatted_reply: str,
    kb_match: bool,
) -> None:
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        separator = "=" * 70

        entry = f"""
{separator}
[{timestamp}] KB Match: {kb_match}
{separator}

USER:
{question}

RAW JSON:
{raw_json}

WHATSAPP REPLY:
{formatted_reply}

"""
        with open(TEST_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as e:
        logger.error("Failed to log conversation: %s", e)


def _extract_metadata(raw_json: str, kb_match: bool) -> dict:
    metadata = {"kb_match": kb_match}
    try:
        data = json.loads(raw_json)
        metadata["intent"] = data.get("type")
        metadata["verdict"] = data.get("verdict")
        metadata["confidence"] = data.get("confidence")
    except Exception:
        metadata["parse_error"] = True
    return metadata


async def _handle_special_command(
    query_text: str,
    user_id: str,
    whatsapp_number: str,
    supabase,
    whatsapp_client: WhatsAppClient,
    message_id: str | None,
) -> bool:
    """Handle footprint/swap commands. Returns True if handled, False to continue normal flow."""
    from app.core.swap_priority import format_swap_priority_message, get_swap_priority

    reply_text = None

    if _is_footprint_command(query_text):
        footprint = await get_user_footprint(supabase, user_id)
        reply_text = format_footprint_message(footprint)

    elif _is_swap_command(query_text):
        swaps = await get_swap_priority(supabase, user_id)
        count = await get_user_product_count(supabase, user_id)
        reply_text = format_swap_priority_message(swaps, count)

    elif is_compare_command(query_text):
        products = extract_comparison_products(query_text)
        if products:
            reply_text = await compare_products(supabase, products[0], products[1])
        else:
            reply_text = "To compare products, try: 'Compare Dove vs Pears'"

    if reply_text is None:
        return False

    await store_message(supabase, user_id, "user", query_text, message_id)
    await store_message(supabase, user_id, "assistant", reply_text)
    await whatsapp_client.send_text_message(whatsapp_number, reply_text)
    await whatsapp_client.send_feedback_buttons(whatsapp_number, message_id or "unknown")
    cmd = "footprint" if _is_footprint_command(query_text) else "swap" if _is_swap_command(query_text) else "compare"
    logger.info("Special command handled: user=%s, command_type=%s", whatsapp_number, cmd)
    return True


async def _is_rate_limited(supabase: Client, user_id: str, limit: int = 30) -> bool:
    try:
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        result = (
            supabase.table("conversations")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("role", "user")
            .gte("timestamp", one_hour_ago)
            .execute()
        )
        count = result.count or 0
        if count >= limit:
            logger.warning("Rate limit hit: user %s sent %d messages in last hour", user_id, count)
            return True
        return False
    except Exception as e:
        logger.error("Rate limit check failed: %s", e)
        return False  # Don't block user if rate limit check fails


def _try_parse_response(raw: str) -> dict | None:
    try:
        return json.loads(raw)
    except Exception:
        return None


_VERDICT_SCORES = {"Safe": 85, "Use with caution": 50, "Avoid": 20}

_NAME_FILLERS = {"this product", "it appears", "it seems", "appears to be", "likely", "generally"}
_NAME_BLOCKLIST = {"product label image", "check this", "is this safe", "hello", "hi", "thanks",
                   "yes", "no", "ok", "sure", "please"}


def _verdict_to_score(verdict: str) -> int:
    return _VERDICT_SCORES.get(verdict, 50)


def _extract_product_name(parsed: dict) -> str | None:
    """Extract a real product name from AI response. Returns None if can't extract a good name."""

    summary = parsed.get("summary", "")
    if not summary:
        return None

    # Try to find capitalized multi-word phrases (product names are usually capitalized)
    caps = re.findall(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+", summary)
    if caps:
        name = max(caps, key=len)
        if len(name) >= 5 and len(name.split()) >= 2:
            return name[:60]

    # Fallback: clean the summary and take first few words
    cleaned = summary
    for filler in _NAME_FILLERS:
        cleaned = cleaned.lower().replace(filler, "")
    cleaned = re.sub(r"[.,!?;:\-]", "", cleaned).strip()
    words = cleaned.split()[:4]
    name = " ".join(words).strip()

    if not name or len(name) < 5 or len(name.split()) < 2:
        return None
    if name.lower() in _NAME_BLOCKLIST:
        return None

    return name[:60]
