import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.message_handler import handle_incoming_message


@pytest.fixture
def mock_whatsapp_client():
    client = AsyncMock()
    client.send_text_message = AsyncMock(return_value={"messages": [{"id": "sent_123"}]})
    client.get_media_url = AsyncMock(return_value="https://cdn.example.com/media")
    client.download_media = AsyncMock(return_value=b"fake_image_bytes")
    return client


@pytest.fixture
def mock_ai_engine():
    engine = AsyncMock()
    engine.get_response = AsyncMock(
        return_value=json.dumps({
            "type": "product_check",
            "verdict": "Use with caution",
            "summary": "Contains some concerning ingredients.",
            "key_ingredients": ["Fragrance"],
            "explanation": "Fragrance may hide harmful chemicals.",
            "suggestion": "Try a fragrance-free option.",
            "follow_up": "Want safer alternatives?",
            "confidence": "high",
        })
    )
    return engine


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.whatsapp_access_token = "test"
    return settings


@pytest.mark.asyncio
class TestMessageHandler:
    @patch("app.core.message_handler.get_or_create_user")
    @patch("app.core.message_handler.is_duplicate_message", return_value=False)
    @patch("app.core.message_handler.lookup_product", return_value=None)
    @patch("app.core.message_handler.log_unknown_query")
    @patch("app.core.message_handler.get_conversation_history", return_value=[])
    @patch("app.core.message_handler.store_message")
    async def test_user_gets_ai_response(
        self,
        mock_store,
        mock_history,
        mock_log_unknown,
        mock_lookup,
        mock_is_dup,
        mock_get_user,
        mock_whatsapp_client,
        mock_ai_engine,
        mock_settings,
        mock_supabase,
    ):
        mock_get_user.return_value = {"id": "user-1", "is_active": True}

        await handle_incoming_message(
            whatsapp_number="+1234567890",
            message_text="Is Dove soap safe?",
            message_type="text",
            message_id="msg-2",
            media_id=None,
            media_mime_type=None,
            supabase=mock_supabase,
            whatsapp_client=mock_whatsapp_client,
            ai_engine=mock_ai_engine,
            settings=mock_settings,
        )

        mock_ai_engine.get_response.assert_called_once()
        assert mock_whatsapp_client.send_text_message.call_count == 1

    @patch("app.core.message_handler.get_or_create_user")
    @patch("app.core.message_handler.is_duplicate_message", return_value=True)
    async def test_duplicate_message_skipped(
        self,
        mock_is_dup,
        mock_get_user,
        mock_whatsapp_client,
        mock_ai_engine,
        mock_settings,
        mock_supabase,
    ):
        await handle_incoming_message(
            whatsapp_number="+1234567890",
            message_text="Hello",
            message_type="text",
            message_id="msg-dup",
            media_id=None,
            media_mime_type=None,
            supabase=mock_supabase,
            whatsapp_client=mock_whatsapp_client,
            ai_engine=mock_ai_engine,
            settings=mock_settings,
        )

        mock_whatsapp_client.send_text_message.assert_not_called()
        mock_ai_engine.get_response.assert_not_called()
