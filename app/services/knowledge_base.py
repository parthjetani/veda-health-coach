import logging

from supabase import Client

from app.core.product_scorer import calculate_score
from app.db.queries.health_items import list_health_items, search_health_items

logger = logging.getLogger(__name__)

_VERDICT_KEYWORDS = {"Safe", "Use with caution", "Avoid"}


async def lookup_product(supabase: Client, query: str) -> dict | None:
    results = await search_health_items(supabase, query)
    if not results:
        return None

    # Return the best match
    best = results[0]
    logger.info(
        "KB match: '%s' → '%s' (score: %.2f)",
        query,
        best.get("item_name"),
        best.get("similarity_score", 0),
    )
    return best


def format_product_context(item: dict) -> str:
    lines = []
    lines.append(f"Product: {item['item_name']}")

    if item.get("brand"):
        lines.append(f"Brand: {item['brand']}")

    if item.get("category"):
        lines.append(f"Category: {item['category']}")

    if item.get("risk_level"):
        lines.append(f"Risk Level: {item['risk_level']}")

    if item.get("confidence_source"):
        lines.append(f"Data Source: {item['confidence_source']}")

    # Full ingredient list (if available)
    ingredients = item.get("ingredients", [])
    if ingredients:
        lines.append(f"Full Ingredients: {', '.join(ingredients)}")

    # Structured flagged ingredients
    flagged = item.get("flagged_ingredients", [])
    if flagged:
        flagged_lines = []
        for f in flagged:
            if isinstance(f, dict):
                name = f.get("name", "")
                reason = f.get("reason", "")
                risk = f.get("risk", "")
                entry = name
                if reason:
                    entry += f" - {reason}"
                if risk:
                    entry += f" ({risk} risk)"
                flagged_lines.append(entry)
            else:
                flagged_lines.append(str(f))
        lines.append(f"Flagged Ingredients: {'; '.join(flagged_lines)}")

    if item.get("ewg_rating"):
        ewg = item["ewg_rating"]
        try:
            ewg_num = int(ewg)
            concern = "Low concern" if ewg_num <= 2 else "Moderate concern" if ewg_num <= 6 else "High concern"
            lines.append(f"Safety Database Rating: {concern} ({ewg_num}/10)")
        except (ValueError, TypeError):
            lines.append(f"Safety Database Rating: {ewg}/10")

    if item.get("recommendation"):
        lines.append(f"Recommendation: {item['recommendation']}")

    if item.get("alternative_brand"):
        lines.append(f"Safer Alternative: {item['alternative_brand']}")

    if item.get("notes"):
        lines.append(f"Notes: {item['notes']}")

    return "\n".join(lines)


async def build_swap_context(supabase: Client, item: dict) -> str | None:
    alt_name = item.get("alternative_brand")
    if not alt_name:
        return None

    # Try to find the alternative product in our DB
    alt_results = await search_health_items(supabase, alt_name)
    if not alt_results:
        return None

    alt = alt_results[0]

    # Only build swap if the alternative is genuinely better
    risk_order = {"low": 0, "medium": 1, "high": 2}
    current_risk = risk_order.get(item.get("risk_level", "medium"), 1)
    alt_risk = risk_order.get(alt.get("risk_level", "medium"), 1)

    if alt_risk >= current_risk:
        return None

    # Calculate scores for both products
    current_score = calculate_score(item)
    alt_score = calculate_score(alt)
    delta = alt_score - current_score

    # Build before/after comparison
    lines = []
    lines.append("SWAP COMPARISON:")
    lines.append(f"CURRENT: {item['item_name']} (Score: {current_score}/100)")

    flagged = item.get("flagged_ingredients", [])
    if flagged:
        names = []
        for f in flagged:
            names.append(f.get("name", str(f)) if isinstance(f, dict) else str(f))
        lines.append(f"  Concerns: {', '.join(names)}")

    lines.append(f"SWAP TO: {alt['item_name']} (Score: {alt_score}/100)")

    alt_flagged = alt.get("flagged_ingredients", [])
    if alt_flagged:
        alt_names = []
        for f in alt_flagged:
            alt_names.append(f.get("name", str(f)) if isinstance(f, dict) else str(f))
        lines.append(f"  Minor concerns: {', '.join(alt_names)}")
    else:
        lines.append("  No major concerns found")

    if alt.get("brand"):
        lines.append(f"  Brand: {alt['brand']}")

    lines.append(f"Improvement: +{delta} points")

    logger.info("Built swap context: %s (%d) -> %s (%d)", item["item_name"], current_score, alt["item_name"], alt_score)
    return "\n".join(lines)


async def lookup_alternatives(supabase: Client, history: list[dict]) -> str | None:
    # Find the last assistant message that was a product check (contains a verdict)
    last_product_msg = None
    for msg in reversed(history):
        if msg.get("role") == "assistant":
            text = msg.get("message_text", "")
            if any(kw in text for kw in _VERDICT_KEYWORDS):
                last_product_msg = text
                break

    if not last_product_msg:
        return None

    # Re-identify the product from that message
    results = await search_health_items(supabase, last_product_msg)
    if not results:
        return None

    original = results[0]
    category = original.get("category")
    alt_brand = original.get("alternative_brand")

    # Build alternatives context
    lines = []
    lines.append(f"Previously discussed: {original['item_name']} ({original.get('risk_level', 'unknown')} risk)")

    if alt_brand:
        lines.append(f"Recommended alternative: {alt_brand}")

    # Fetch low-risk products in the same category
    if category:
        alternatives, _ = await list_health_items(
            supabase, page=1, per_page=5, category=category, risk_level="low"
        )
        if alternatives:
            lines.append(f"\nOther low-risk options in {category}:")
            for item in alternatives:
                brand = f" ({item['brand']})" if item.get("brand") else ""
                lines.append(f"- {item['item_name']}{brand}")

    if len(lines) <= 1 and not alt_brand:
        return None

    logger.info("Built alternatives context for %s", original["item_name"])
    return "\n".join(lines)
