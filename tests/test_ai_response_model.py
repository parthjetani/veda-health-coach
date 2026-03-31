import json

import pytest
from pydantic import ValidationError

from app.models.ai_response import AIResponse


class TestAIResponse:
    def test_valid_product_check(self):
        data = {
            "type": "product_check",
            "verdict": "Safe",
            "summary": "This product looks clean.",
            "key_ingredients": [],
            "explanation": None,
            "suggestion": "Keep using it.",
            "follow_up": "Want even cleaner options?",
            "confidence": "high",
        }
        resp = AIResponse(**data)
        assert resp.type == "product_check"
        assert resp.verdict == "Safe"
        assert resp.confidence == "high"

    def test_valid_general_advice(self):
        data = {
            "type": "general_advice",
            "verdict": None,
            "summary": "Water is important for health.",
            "key_ingredients": [],
            "explanation": "Helps flush toxins.",
            "suggestion": "Drink 8 glasses a day.",
            "follow_up": "Want hydration tips?",
            "confidence": "high",
        }
        resp = AIResponse(**data)
        assert resp.verdict is None
        assert resp.type == "general_advice"

    def test_invalid_type(self):
        data = {
            "type": "unknown_type",
            "verdict": None,
            "summary": "Test",
            "key_ingredients": [],
            "explanation": None,
            "suggestion": None,
            "follow_up": None,
            "confidence": "high",
        }
        with pytest.raises(ValidationError):
            AIResponse(**data)

    def test_invalid_verdict(self):
        data = {
            "type": "product_check",
            "verdict": "Maybe",
            "summary": "Test",
            "key_ingredients": [],
            "explanation": None,
            "suggestion": None,
            "follow_up": None,
            "confidence": "high",
        }
        with pytest.raises(ValidationError):
            AIResponse(**data)

    def test_invalid_confidence(self):
        data = {
            "type": "product_check",
            "verdict": "Safe",
            "summary": "Test",
            "key_ingredients": [],
            "explanation": None,
            "suggestion": None,
            "follow_up": None,
            "confidence": "uncertain",
        }
        with pytest.raises(ValidationError):
            AIResponse(**data)

    def test_empty_summary_rejected(self):
        data = {
            "type": "product_check",
            "verdict": "Safe",
            "summary": "",
            "key_ingredients": [],
            "explanation": None,
            "suggestion": None,
            "follow_up": None,
            "confidence": "high",
        }
        with pytest.raises(ValidationError):
            AIResponse(**data)

    def test_null_key_ingredients_becomes_empty_list(self):
        data = {
            "type": "product_check",
            "verdict": "Safe",
            "summary": "Clean product.",
            "key_ingredients": None,
            "explanation": None,
            "suggestion": None,
            "follow_up": None,
            "confidence": "high",
        }
        resp = AIResponse(**data)
        assert resp.key_ingredients == []

    def test_model_validate_json(self, sample_ai_json_response):
        resp = AIResponse.model_validate_json(sample_ai_json_response)
        assert resp.type == "product_check"
        assert resp.verdict == "Use with caution"
        assert "Fragrance" in resp.key_ingredients
        assert resp.confidence == "high"
