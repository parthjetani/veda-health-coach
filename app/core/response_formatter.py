import json
import logging
import random
import re

from app.models.ai_response import AIResponse

logger = logging.getLogger(__name__)

WHATSAPP_MAX_LENGTH = 4096

VERDICT_EMOJI = {
    "Safe": "✅ Safe",
    "Use with caution": "⚠️ Use with caution",
    "Avoid": "🚫 Avoid",
}


def parse_and_format(
    raw: str,
    product_score: int | None = None,
    progress: dict | None = None,
) -> str:
    try:
        cleaned = _extract_json(raw)
        data = AIResponse.model_validate_json(cleaned)
        return _build_whatsapp_message(data, product_score, progress)
    except Exception as e:
        logger.warning("Failed to parse AI JSON response: %s", e)
        # Never send raw JSON to user — if fallback text looks like JSON, send generic message
        stripped = _strip_markdown(raw)
        if stripped.strip().startswith("{"):
            return "I had trouble analyzing that fully. Could you try again or send a clearer photo?"
        return stripped[:WHATSAPP_MAX_LENGTH]


def _extract_json(raw: str) -> str:
    raw = raw.strip()

    # Strip ```json ... ``` code blocks
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*\n?", "", raw)
        raw = re.sub(r"\n?```\s*$", "", raw)

    # Find the JSON object boundaries
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw[start : end + 1]

    return raw


def _build_whatsapp_message(
    data: AIResponse,
    product_score: int | None = None,
    progress: dict | None = None,
) -> str:
    from app.core.product_scorer import format_score_line

    parts = []

    # 1. Score line (if product check with KB match)
    if product_score is not None and data.type == "product_check":
        parts.append(format_score_line(product_score))

    # 2. Verdict line (aligned with score when KB match)
    if data.verdict:
        verdict = data.verdict
        if product_score is not None:
            # Override AI verdict to match our deterministic score
            if product_score >= 80:
                verdict = "Safe"
            elif product_score >= 40:
                verdict = "Use with caution"
            else:
                verdict = "Avoid"
        verdict_text = VERDICT_EMOJI.get(verdict, verdict)
        parts.append(verdict_text)

    # 2. Summary (always present)
    parts.append(data.summary)

    # 3. Key ingredients
    if data.key_ingredients:
        ingredients = "\n".join(f"• {ing}" for ing in data.key_ingredients)
        parts.append(f"Key concerns:\n{ingredients}")

    # 4. Explanation
    if data.explanation:
        parts.append(data.explanation)

    # 5. Suggestion (fix inline bullets from AI)
    if data.suggestion:
        suggestion = data.suggestion
        # Split inline bullets onto separate lines
        if "• " in suggestion and suggestion.count("• ") > 1:
            suggestion = suggestion.replace(" • ", "\n• ")
        parts.append(suggestion)

    # 6. Confidence-based tone (only if AI didn't already express uncertainty in summary)
    summary_lower = data.summary.lower() if data.summary else ""
    already_uncertain = any(phrase in summary_lower for phrase in [
        "i don't see", "i couldn't", "not sure", "may be wrong", "not clear",
    ])
    if data.confidence == "low" and not already_uncertain:
        parts.append(
            "I might be off here - could you share the full ingredient list for a better check?"
        )
    elif data.confidence == "medium" and data.type == "product_check" and not already_uncertain:
        parts.append(
            "This is based on general knowledge. For a more accurate check, send the ingredient list or a photo."
        )

    # 7. Progress feedback
    if progress:
        delta = progress.get("delta", 0)
        if delta > 0 and progress.get("previous_avg") is not None:
            parts.append(
                f"Your average product score went from {progress['previous_avg']} to {progress['current_avg']} (+{delta})"
            )
        removed = progress.get("high_risk_removed_since_start", 0)
        if removed > 0:
            parts.append(f"You've reduced {removed} high-risk product(s) from your routine")
        if progress.get("milestone"):
            parts.append(progress["milestone"])
        if progress.get("nudge"):
            parts.append(progress["nudge"])

    # 8. Follow-up
    if data.follow_up:
        parts.append(data.follow_up)

    # 9. Share prompt (product checks only, ~30% of the time to avoid spam)
    if data.type == "product_check" and data.verdict and data.confidence != "low":
        if random.random() < 0.3:
            parts.append(
                "Know someone who uses this product? Forward this to them!"
            )

    message = "\n\n".join(parts)
    return message[:WHATSAPP_MAX_LENGTH]


def _strip_markdown(text: str) -> str:
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    # Remove bold
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    # Remove italic
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    # Remove headers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Replace markdown bullets with •
    text = re.sub(r"^[-*]\s+", "• ", text, flags=re.MULTILINE)
    return text.strip()
