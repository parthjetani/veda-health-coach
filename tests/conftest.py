import os
from unittest.mock import AsyncMock, MagicMock

import pytest

# Force-set dummy env vars so real credentials in .env can never leak into tests
os.environ["WHATSAPP_ACCESS_TOKEN"] = "test-token"
os.environ["WHATSAPP_PHONE_NUMBER_ID"] = "123456789"
os.environ["WHATSAPP_VERIFY_TOKEN"] = "test-verify-token"
os.environ["WHATSAPP_APP_SECRET"] = ""
os.environ["GEMINI_API_KEY"] = "test-gemini-key"
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-service-role-key"
os.environ["ADMIN_API_KEY"] = "test-admin-key"
# Remove old Anthropic vars that may linger in .env
os.environ.pop("ANTHROPIC_API_KEY", None)

# Clear settings cache so tests use test env vars
from app.config import get_settings
get_settings.cache_clear()


@pytest.fixture
def mock_supabase():
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_http_client():
    mock = AsyncMock()
    return mock


@pytest.fixture
def sample_whatsapp_text_payload():
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "BUSINESS_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "16505551234",
                                "phone_number_id": "123456789",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Test User"},
                                    "wa_id": "16505559876",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "16505559876",
                                    "id": "wamid.test123",
                                    "timestamp": "1234567890",
                                    "text": {"body": "Is Dove soap safe?"},
                                    "type": "text",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


@pytest.fixture
def sample_whatsapp_image_payload():
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "BUSINESS_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "16505551234",
                                "phone_number_id": "123456789",
                            },
                            "messages": [
                                {
                                    "from": "16505559876",
                                    "id": "wamid.img456",
                                    "timestamp": "1234567890",
                                    "type": "image",
                                    "image": {
                                        "id": "media_id_123",
                                        "mime_type": "image/jpeg",
                                        "sha256": "abc123",
                                        "caption": "Check this product",
                                    },
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


@pytest.fixture
def sample_whatsapp_status_payload():
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "BUSINESS_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "16505551234",
                                "phone_number_id": "123456789",
                            },
                            "statuses": [
                                {
                                    "id": "wamid.status789",
                                    "status": "delivered",
                                    "timestamp": "1234567890",
                                    "recipient_id": "16505559876",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


@pytest.fixture
def sample_ai_json_response():
    return '{"type": "product_check", "verdict": "Use with caution", "summary": "This product is generally okay but has a few ingredients worth limiting.", "key_ingredients": ["Fragrance", "Parabens"], "explanation": "Fragrance may irritate skin, and parabens have been linked in studies to hormone disruption.", "suggestion": "Look for fragrance-free, paraben-free options.", "follow_up": "Want safer alternatives?", "confidence": "high"}'


@pytest.fixture
def sample_ai_safe_response():
    return '{"type": "product_check", "verdict": "Safe", "summary": "This product looks clean with no major concerns.", "key_ingredients": [], "explanation": null, "suggestion": "Good choice for everyday use.", "follow_up": "Want even cleaner options?", "confidence": "high"}'


@pytest.fixture
def sample_ai_general_response():
    return '{"type": "general_advice", "verdict": null, "summary": "Drinking enough water helps your body flush out waste and keeps your skin healthy.", "key_ingredients": [], "explanation": "Most adults need about 8 glasses a day, but it depends on your activity level.", "suggestion": "Try keeping a water bottle with you throughout the day.", "follow_up": "Want tips on building better hydration habits?", "confidence": "high"}'
