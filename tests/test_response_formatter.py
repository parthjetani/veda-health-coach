import json

from app.core.response_formatter import parse_and_format, _extract_json, _strip_markdown


class TestParseAndFormat:
    def test_product_check_caution(self, sample_ai_json_response):
        result = parse_and_format(sample_ai_json_response)
        assert "⚠️ Use with caution" in result
        assert "Fragrance" in result
        assert "Parabens" in result
        assert "Want safer alternatives?" in result

    def test_product_check_safe(self, sample_ai_safe_response):
        result = parse_and_format(sample_ai_safe_response)
        assert "✅ Safe" in result
        assert "Good choice" in result
        assert "Want even cleaner options?" in result

    def test_general_advice_no_verdict(self, sample_ai_general_response):
        result = parse_and_format(sample_ai_general_response)
        assert "✅" not in result
        assert "⚠️" not in result
        assert "🚫" not in result
        assert "water" in result.lower()

    def test_avoid_verdict(self):
        data = {
            "type": "product_check",
            "verdict": "Avoid",
            "summary": "This product contains harmful chemicals.",
            "key_ingredients": ["BPA", "Triclosan"],
            "explanation": "Both are known hormone disruptors.",
            "suggestion": "Switch to a safer product immediately.",
            "follow_up": "Want safer alternatives?",
            "confidence": "high",
        }
        result = parse_and_format(json.dumps(data))
        assert "🚫 Avoid" in result
        assert "BPA" in result
        assert "Triclosan" in result

    def test_low_confidence_disclaimer(self):
        data = {
            "type": "product_check",
            "verdict": "Use with caution",
            "summary": "Not sure about this one.",
            "key_ingredients": [],
            "explanation": None,
            "suggestion": None,
            "follow_up": None,
            "confidence": "low",
        }
        result = parse_and_format(json.dumps(data))
        assert "might be off" in result

    def test_fallback_on_invalid_json(self):
        result = parse_and_format("This is not JSON at all")
        assert result == "This is not JSON at all"

    def test_fallback_on_partial_json(self):
        result = parse_and_format('{"type": "product_check"}')
        # Should fallback since required fields are missing
        assert "product_check" in result

    def test_handles_code_block_wrapped_json(self, sample_ai_json_response):
        wrapped = f"```json\n{sample_ai_json_response}\n```"
        result = parse_and_format(wrapped)
        assert "⚠️ Use with caution" in result

    def test_truncation(self):
        data = {
            "type": "general_advice",
            "verdict": None,
            "summary": "A" * 5000,
            "key_ingredients": [],
            "explanation": None,
            "suggestion": None,
            "follow_up": None,
            "confidence": "high",
        }
        result = parse_and_format(json.dumps(data))
        assert len(result) <= 4096


class TestScoreInFormatter:
    def test_product_check_with_score(self, sample_ai_json_response):
        result = parse_and_format(sample_ai_json_response, product_score=85)
        assert "Score: 85/100 (Excellent)" in result
        # Score 85 overrides verdict to "Safe" (aligned)
        assert "Safe" in result
        score_pos = result.find("Score:")
        verdict_pos = result.find("Safe")
        assert score_pos < verdict_pos

    def test_product_check_without_score(self, sample_ai_json_response):
        result = parse_and_format(sample_ai_json_response, product_score=None)
        assert "Score:" not in result

    def test_general_advice_ignores_score(self, sample_ai_general_response):
        result = parse_and_format(sample_ai_general_response, product_score=85)
        assert "Score:" not in result

    def test_score_boundary_zero(self):
        data = {
            "type": "product_check",
            "verdict": "Avoid",
            "summary": "Very concerning product.",
            "key_ingredients": ["BPA"],
            "explanation": "Multiple high-risk ingredients.",
            "suggestion": "Replace immediately.",
            "follow_up": "Want safer options?",
            "confidence": "high",
        }
        result = parse_and_format(json.dumps(data), product_score=0)
        assert "Score: 0/100 (Bad)" in result

    def test_score_boundary_hundred(self):
        data = {
            "type": "product_check",
            "verdict": "Safe",
            "summary": "Perfectly clean product.",
            "key_ingredients": [],
            "explanation": "No concerns at all.",
            "suggestion": "Great choice.",
            "follow_up": "Want even cleaner options?",
            "confidence": "high",
        }
        result = parse_and_format(json.dumps(data), product_score=100)
        assert "Score: 100/100 (Excellent)" in result


class TestExtractJson:
    def test_plain_json(self):
        result = _extract_json('{"key": "value"}')
        assert result == '{"key": "value"}'

    def test_code_block(self):
        result = _extract_json('```json\n{"key": "value"}\n```')
        assert '"key"' in result

    def test_json_with_surrounding_text(self):
        result = _extract_json('Here is the response: {"key": "value"} end')
        assert result == '{"key": "value"}'


class TestStripMarkdown:
    def test_bold(self):
        assert _strip_markdown("This is **bold** text") == "This is bold text"

    def test_italic(self):
        assert _strip_markdown("This is *italic* text") == "This is italic text"

    def test_headers(self):
        assert _strip_markdown("## Header\nContent") == "Header\nContent"

    def test_bullets(self):
        assert _strip_markdown("- item 1\n- item 2") == "• item 1\n• item 2"
