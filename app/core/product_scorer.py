"""
Product Verdict Score (0-100)

Deterministic scoring algorithm - no AI dependency.
Calculates a score based on flagged ingredients and their risk levels.
Designed to be consistent, explainable, and shareable.

Score ranges:
  80-100  Excellent - Clean product, minimal concerns
  60-79   Good      - Minor concerns, fine for most people
  40-59   Fair      - Notable concerns, consider alternatives
  20-39   Poor      - Multiple concerning ingredients
  0-19    Bad       - Serious concerns, strongly recommend swapping
"""

import logging

logger = logging.getLogger(__name__)

# Points deducted per flagged ingredient by risk level
RISK_DEDUCTIONS = {
    "high": 30,
    "medium": 15,
    "low": 5,
}

# Score range labels
SCORE_LABELS = [
    (80, "Excellent"),
    (60, "Good"),
    (40, "Fair"),
    (20, "Poor"),
    (0, "Bad"),
]


def calculate_score(item: dict) -> int:
    score = 100

    flagged = item.get("flagged_ingredients", [])
    for ingredient in flagged:
        if isinstance(ingredient, dict):
            risk = ingredient.get("risk", "medium")
        else:
            risk = "medium"
        score -= RISK_DEDUCTIONS.get(risk, 10)

    return max(0, min(100, score))


def get_score_label(score: int) -> str:
    for threshold, label in SCORE_LABELS:
        if score >= threshold:
            return label
    return "Bad"


def format_score_breakdown(item: dict) -> str:
    """Build a human-readable score breakdown showing point deductions."""
    score = 100
    lines = []

    flagged = item.get("flagged_ingredients", [])
    for ingredient in flagged:
        if isinstance(ingredient, dict):
            name = ingredient.get("name", "Unknown")
            reason = ingredient.get("reason", "")
            risk = ingredient.get("risk", "medium")
        else:
            name = str(ingredient)
            reason = ""
            risk = "medium"

        deduction = RISK_DEDUCTIONS.get(risk, 10)
        score -= deduction

        detail = f"-{deduction} pts: {name}"
        if reason:
            detail += f" ({reason})"
        lines.append(detail)

    if not lines:
        lines.append("No concerning ingredients found")

    final_score = max(0, min(100, score))
    label = get_score_label(final_score)

    return f"Score: {final_score}/100 ({label})\n" + "\n".join(lines)


def format_score_line(score: int) -> str:
    """Single-line score for WhatsApp message header."""
    label = get_score_label(score)
    return f"Score: {score}/100 ({label})"
