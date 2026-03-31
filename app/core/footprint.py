"""
Personal Chemical Footprint

Analyzes a user's complete product history to show:
- Total products checked and average score
- Top chemical exposures across all products
- Highest risk product and best product
- Best swap for maximum improvement
- Score trend over time
"""

import logging
from collections import Counter

from supabase import Client

from app.core.product_scorer import calculate_score, get_score_label
from app.db.queries.health_items import search_health_items
from app.db.queries.user_products import get_user_products_with_items

logger = logging.getLogger(__name__)


async def get_user_footprint(supabase: Client, user_id: str) -> dict:
    products = await get_user_products_with_items(supabase, user_id)

    if not products:
        return {"total_products": 0}

    # Calculate basics
    scores = [p["score"] for p in products if p.get("score") is not None]
    avg_score = round(sum(scores) / len(scores)) if scores else 0

    # Top exposures: count flagged ingredients across all products
    top_exposures = _get_top_exposures(products)

    # Highest risk (lowest score) and best product (highest score)
    scored_products = [p for p in products if p.get("score") is not None]
    highest_risk = min(scored_products, key=lambda p: p["score"]) if scored_products else None
    best_product = max(scored_products, key=lambda p: p["score"]) if scored_products else None

    # Best swap: lowest-scoring product that has an alternative in DB
    best_swap = await _get_best_swap(supabase, products)

    # Score trend (chronological order)
    score_trend = _get_score_trend(products)

    return {
        "total_products": len(products),
        "average_score": avg_score,
        "average_label": get_score_label(avg_score),
        "top_exposures": top_exposures[:5],
        "highest_risk_product": {
            "name": highest_risk["product_name"],
            "score": highest_risk["score"],
        } if highest_risk else None,
        "best_product": {
            "name": best_product["product_name"],
            "score": best_product["score"],
        } if best_product else None,
        "best_swap": best_swap,
        "score_trend": score_trend,
    }


def _get_top_exposures(products: list[dict]) -> list[dict]:
    ingredient_counter = Counter()
    total = len(products)

    for product in products:
        item_data = product.get("health_items")
        if not item_data:
            continue

        flagged = item_data.get("flagged_ingredients", [])
        for ing in flagged:
            if isinstance(ing, dict):
                name = ing.get("name", "")
            else:
                name = str(ing)
            if name:
                ingredient_counter[name] += 1

    return [
        {
            "ingredient": name,
            "count": count,
            "percentage": round(count / total * 100) if total > 0 else 0,
        }
        for name, count in ingredient_counter.most_common()
    ]


async def _get_best_swap(supabase: Client, products: list[dict]) -> dict | None:
    # Find lowest-scoring product with an alternative
    candidates = []
    for product in products:
        item_data = product.get("health_items")
        if not item_data or not item_data.get("alternative_brand"):
            continue
        score = product.get("score", 100)
        candidates.append((score, product, item_data))

    if not candidates:
        return None

    # Sort by score ascending (worst product first)
    candidates.sort(key=lambda x: x[0])
    worst_score, worst_product, worst_item = candidates[0]

    # Look up the alternative
    alt_name = worst_item["alternative_brand"]
    alt_results = await search_health_items(supabase, alt_name)
    if not alt_results:
        return {
            "current": worst_product["product_name"],
            "current_score": worst_score,
            "replacement": alt_name,
            "replacement_score": None,
            "impact": None,
        }

    alt = alt_results[0]
    alt_score = calculate_score(alt)

    return {
        "current": worst_product["product_name"],
        "current_score": worst_score,
        "replacement": alt["item_name"],
        "replacement_score": alt_score,
        "impact": alt_score - worst_score,
    }


def _get_score_trend(products: list[dict]) -> list[int]:
    # Chronological scores (oldest first)
    scored = [
        p["score"]
        for p in reversed(products)
        if p.get("score") is not None
    ]
    return scored


async def get_progress(supabase: Client, user_id: str) -> dict | None:
    """Calculate progress since last product check. Returns None if < 2 products."""
    from app.db.queries.user_products import get_user_products

    products = await get_user_products(supabase, user_id)
    scored = [p for p in products if p.get("score") is not None]

    if len(scored) < 2:
        # First product — return milestone only
        if len(scored) == 1:
            return {
                "previous_avg": None,
                "current_avg": scored[0]["score"],
                "delta": 0,
                "total_products": 1,
                "high_risk_count": 1 if scored[0]["score"] < 40 else 0,
                "high_risk_removed_since_start": 0,
                "milestone": "Great start! Keep checking your daily products.",
            }
        return None

    scores = [p["score"] for p in scored]
    # Products are ordered by last_checked_at DESC, so [0] is newest
    all_except_last = scores[1:]
    previous_avg = round(sum(all_except_last) / len(all_except_last))
    current_avg = round(sum(scores) / len(scores))
    delta = current_avg - previous_avg

    # High-risk tracking
    high_risk_count = sum(1 for s in scores if s < 40)
    # Compare against first 3 products to see if high-risk count decreased
    early_scores = scores[-min(3, len(scores)):]
    early_high_risk = sum(1 for s in early_scores if s < 40)
    high_risk_removed = max(0, early_high_risk - high_risk_count)

    # Check milestones
    total = len(scored)
    milestone = None
    if total == 5:
        milestone = "You've checked 5 products! Type 'my footprint' to see your full summary."
    elif current_avg >= 80 and previous_avg < 80:
        milestone = "Incredible - your products are cleaner than most people's!"
    elif current_avg >= 60 and previous_avg < 60:
        milestone = "Your average score just crossed 60 - real progress!"

    return {
        "previous_avg": previous_avg,
        "current_avg": current_avg,
        "delta": delta,
        "total_products": total,
        "high_risk_count": high_risk_count,
        "high_risk_removed_since_start": high_risk_removed,
        "milestone": milestone,
    }


def format_footprint_message(footprint: dict) -> str:
    if footprint.get("total_products", 0) == 0:
        return "You haven't checked any products yet! Send me a product name or photo to get started."

    parts = []

    # Header
    parts.append(f"Your Chemical Footprint ({footprint['total_products']} products)")
    parts.append(f"Average Score: {footprint['average_score']}/100 ({footprint['average_label']})")

    # Top exposures
    exposures = footprint.get("top_exposures", [])
    if exposures:
        exp_lines = []
        for exp in exposures[:3]:
            exp_lines.append(
                f"  {exp['ingredient']}: in {exp['count']} of {footprint['total_products']} products ({exp['percentage']}%)"
            )
        parts.append("Your top exposures:\n" + "\n".join(exp_lines))

    # Highest risk
    highest = footprint.get("highest_risk_product")
    if highest:
        parts.append(f"Highest risk: {highest['name']} (Score: {highest['score']}/100)")

    # Best swap
    swap = footprint.get("best_swap")
    if swap and swap.get("impact"):
        parts.append(
            f"Best swap for biggest impact:\n"
            f"  Replace {swap['current']} ({swap['current_score']}) "
            f"with {swap['replacement']} ({swap['replacement_score']})\n"
            f"  Improvement: +{swap['impact']} points"
        )

    # Score trend
    trend = footprint.get("score_trend", [])
    if len(trend) >= 3:
        recent = trend[-3:]
        parts.append(f"Recent trend: {' -> '.join(str(s) for s in recent)}")

    return "\n\n".join(parts)
