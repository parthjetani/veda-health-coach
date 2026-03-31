from app.core.product_scorer import (
    calculate_score,
    format_score_breakdown,
    format_score_line,
    get_score_label,
)


class TestCalculateScore:
    def test_clean_product_scores_100(self):
        item = {"flagged_ingredients": []}
        assert calculate_score(item) == 100

    def test_no_flagged_key_scores_100(self):
        item = {}
        assert calculate_score(item) == 100

    def test_single_high_risk(self):
        item = {"flagged_ingredients": [{"name": "BPA", "risk": "high"}]}
        assert calculate_score(item) == 70

    def test_single_medium_risk(self):
        item = {"flagged_ingredients": [{"name": "Fragrance", "risk": "medium"}]}
        assert calculate_score(item) == 85

    def test_single_low_risk(self):
        item = {"flagged_ingredients": [{"name": "BHT", "risk": "low"}]}
        assert calculate_score(item) == 95

    def test_multiple_ingredients(self):
        item = {
            "flagged_ingredients": [
                {"name": "DMDM Hydantoin", "risk": "high"},
                {"name": "SLS", "risk": "medium"},
                {"name": "Fragrance", "risk": "medium"},
                {"name": "Dimethicone", "risk": "low"},
            ]
        }
        # 100 - 30 - 15 - 15 - 5 = 35
        assert calculate_score(item) == 35

    def test_score_never_below_zero(self):
        item = {
            "flagged_ingredients": [
                {"name": "A", "risk": "high"},
                {"name": "B", "risk": "high"},
                {"name": "C", "risk": "high"},
                {"name": "D", "risk": "high"},
            ]
        }
        # 100 - 30*4 = -20 -> clamped to 0
        assert calculate_score(item) == 0

    def test_flat_string_ingredients_default_to_medium(self):
        item = {"flagged_ingredients": ["Fragrance", "Parabens"]}
        # 100 - 15 - 15 = 70
        assert calculate_score(item) == 70

    def test_mixed_format(self):
        item = {
            "flagged_ingredients": [
                {"name": "Fragrance", "risk": "medium"},
                "Parabens",
            ]
        }
        # 100 - 15 - 15 = 70
        assert calculate_score(item) == 70


class TestGetScoreLabel:
    def test_excellent(self):
        assert get_score_label(100) == "Excellent"
        assert get_score_label(80) == "Excellent"

    def test_good(self):
        assert get_score_label(79) == "Good"
        assert get_score_label(60) == "Good"

    def test_fair(self):
        assert get_score_label(59) == "Fair"
        assert get_score_label(40) == "Fair"

    def test_poor(self):
        assert get_score_label(39) == "Poor"
        assert get_score_label(20) == "Poor"

    def test_bad(self):
        assert get_score_label(19) == "Bad"
        assert get_score_label(0) == "Bad"


class TestFormatScoreLine:
    def test_high_score(self):
        result = format_score_line(85)
        assert "85/100" in result
        assert "Excellent" in result

    def test_low_score(self):
        result = format_score_line(35)
        assert "35/100" in result
        assert "Poor" in result


class TestFormatScoreBreakdown:
    def test_clean_product(self):
        item = {"flagged_ingredients": []}
        result = format_score_breakdown(item)
        assert "100/100" in result
        assert "Excellent" in result
        assert "No concerning ingredients" in result

    def test_with_flagged(self):
        item = {
            "flagged_ingredients": [
                {"name": "Fragrance", "reason": "undisclosed chemicals", "risk": "medium"},
                {"name": "BHT", "reason": "synthetic preservative", "risk": "low"},
            ]
        }
        result = format_score_breakdown(item)
        assert "80/100" in result
        assert "-15 pts: Fragrance" in result
        assert "-5 pts: BHT" in result

    def test_multiple_high_risk(self):
        item = {
            "flagged_ingredients": [
                {"name": "DMDM Hydantoin", "risk": "high"},
                {"name": "Oxybenzone", "risk": "high"},
            ]
        }
        result = format_score_breakdown(item)
        assert "40/100" in result
        assert "Fair" in result
