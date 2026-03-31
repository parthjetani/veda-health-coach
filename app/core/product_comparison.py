"""
Product Comparison Mode

Compares two products side-by-side with scores and ingredient concerns.
Triggered by commands like "Compare Dove vs Pears".
"""

import re
import logging

from supabase import Client

from app.core.product_scorer import calculate_score, get_score_label
from app.db.queries.health_items import search_health_items

logger = logging.getLogger(__name__)

_SPLIT_PATTERN = re.compile(
    r"\b(?:vs\.?|versus|or|compared?\s+to|and)\b",
    re.IGNORECASE,
)

_COMPARE_TRIGGERS = {"compare", "vs", "versus", "which is better", "which is safer"}


def is_compare_command(text: str) -> bool:
    lower = text.strip().lower()
    return any(kw in lower for kw in _COMPARE_TRIGGERS)


def extract_comparison_products(text: str) -> tuple[str, str] | None:
    # Remove common prefixes
    cleaned = re.sub(r"^(compare|check|which is better|which is safer)\s*:?\s*", "", text.strip(), flags=re.IGNORECASE)

    # Split on vs/or/versus/compared to/and
    parts = _SPLIT_PATTERN.split(cleaned, maxsplit=1)

    if len(parts) < 2:
        return None

    a = parts[0].strip().rstrip(".,!?")
    b = parts[1].strip().rstrip(".,!?")

    # Remove trailing "which is better/safer" from second part
    b = re.sub(r"\s*(which is (?:better|safer))\s*\??$", "", b, flags=re.IGNORECASE).strip()

    if not a or not b:
        return None

    return (a, b)


async def compare_products(supabase: Client, query_a: str, query_b: str) -> str:
    result_a = await search_health_items(supabase, query_a)
    result_b = await search_health_items(supabase, query_b)

    product_a = result_a[0] if result_a else None
    product_b = result_b[0] if result_b else None

    if not product_a and not product_b:
        return (
            f"I don't have '{query_a}' or '{query_b}' in my database yet.\n\n"
            "Try checking each product individually first, or send a photo of the label."
        )

    if not product_a:
        return (
            f"I found {product_b['item_name']} but not '{query_a}'.\n\n"
            "Try checking the missing product individually first."
        )

    if not product_b:
        return (
            f"I found {product_a['item_name']} but not '{query_b}'.\n\n"
            "Try checking the missing product individually first."
        )

    score_a = calculate_score(product_a)
    score_b = calculate_score(product_b)
    label_a = get_score_label(score_a)
    label_b = get_score_label(score_b)

    # Build comparison
    parts = ["Product Comparison"]

    # Product A
    block_a = f"{product_a['item_name']}\nScore: {score_a}/100 ({label_a})"
    flagged_a = _format_flagged_bullets(product_a)
    if flagged_a:
        block_a += f"\n{flagged_a}"
    parts.append(block_a)

    parts.append("vs")

    # Product B
    block_b = f"{product_b['item_name']}\nScore: {score_b}/100 ({label_b})"
    flagged_b = _format_flagged_bullets(product_b)
    if flagged_b:
        block_b += f"\n{flagged_b}"
    parts.append(block_b)

    # Winner
    diff = abs(score_a - score_b)
    if diff < 5:
        parts.append("Result: Both products are roughly equal in safety.")
    elif score_a > score_b:
        parts.append(
            f"Winner: {product_a['item_name']} (+{diff} points)\n"
            f"Cleaner formula with fewer concerning ingredients."
        )
    else:
        parts.append(
            f"Winner: {product_b['item_name']} (+{diff} points)\n"
            f"Cleaner formula with fewer concerning ingredients."
        )

    logger.info("Comparison: %s (%d) vs %s (%d)", product_a["item_name"], score_a, product_b["item_name"], score_b)
    return "\n\n".join(parts)


def _format_flagged_bullets(item: dict) -> str:
    flagged = item.get("flagged_ingredients", [])
    names = []
    for f in flagged:
        if isinstance(f, dict):
            name = f.get("name", "")
        else:
            name = str(f)
        if name:
            names.append(f"  \u2022 {name}")
    return "\n".join(names)
