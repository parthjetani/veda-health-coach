"""
Smart Swap Priority

Calculates which product swaps give a user the biggest health improvement,
ranked by impact score. Uses the user's actual product history, not generic
suggestions.
"""

import logging

from supabase import Client

from app.core.product_scorer import calculate_score
from app.db.queries.health_items import search_health_items
from app.db.queries.user_products import get_user_products_with_items

logger = logging.getLogger(__name__)


async def get_swap_priority(supabase: Client, user_id: str) -> list[dict]:
    products = await get_user_products_with_items(supabase, user_id)

    if not products:
        return []

    swaps = []
    for product in products:
        item_data = product.get("health_items")
        if not item_data or not item_data.get("alternative_brand"):
            continue

        current_score = product.get("score") or calculate_score(item_data)

        # Look up the alternative product in DB
        alt_name = item_data["alternative_brand"]
        alt_results = await search_health_items(supabase, alt_name)
        if not alt_results:
            continue

        alt = alt_results[0]
        alt_score = calculate_score(alt)
        impact = alt_score - current_score

        if impact <= 0:
            continue

        # Find which flagged ingredients get removed
        current_flagged = set()
        for f in item_data.get("flagged_ingredients", []):
            name = f.get("name", str(f)) if isinstance(f, dict) else str(f)
            current_flagged.add(name)

        alt_flagged = set()
        for f in alt.get("flagged_ingredients", []):
            name = f.get("name", str(f)) if isinstance(f, dict) else str(f)
            alt_flagged.add(name)

        removed = current_flagged - alt_flagged

        swaps.append({
            "current_name": product["product_name"],
            "current_score": current_score,
            "alt_name": alt["item_name"],
            "alt_score": alt_score,
            "impact": impact,
            "removed_ingredients": list(removed),
        })

    # Sort by impact descending (biggest improvement first)
    swaps.sort(key=lambda x: x["impact"], reverse=True)
    return swaps[:5]


def format_swap_priority_message(swaps: list[dict], total_products: int) -> str:
    if not swaps:
        if total_products == 0:
            return "You haven't checked any products yet! Send me a product name or photo to get started."
        return "I couldn't find swap suggestions for your products. Try checking more products first."

    parts = []
    parts.append(f"Your Swap Priority (based on {total_products} products)")

    for i, swap in enumerate(swaps[:3], 1):
        removed_str = ""
        if swap["removed_ingredients"]:
            removed_str = f"\n   Removes: {', '.join(swap['removed_ingredients'][:3])}"

        parts.append(
            f"{i}. {swap['current_name']} -> {swap['alt_name']}\n"
            f"   Score: {swap['current_score']} -> {swap['alt_score']} "
            f"(+{swap['impact']} points){removed_str}"
        )

    # Summary
    if len(swaps) >= 2:
        top_two_impact = swaps[0]["impact"] + swaps[1]["impact"]
        parts.append(
            f"Swapping just #1 and #2 improves your average by ~{top_two_impact // 2} points."
        )

    return "\n\n".join(parts)
