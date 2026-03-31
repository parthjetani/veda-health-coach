import logging
import re

import httpx

from app.config import Settings
from app.core.errors import WhatsApp24hWindowError

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
_24H_ERROR_CODES = {"131047", "131031"}  # WhatsApp 24h window error codes
WHATSAPP_MAX_MESSAGE_LENGTH = 4096


def normalize_phone_number(phone: str) -> str:
    digits = re.sub(r"[^\d+]", "", phone)
    if not digits.startswith("+"):
        digits = f"+{digits}"
    return digits


class WhatsAppClient:
    def __init__(self, http_client: httpx.AsyncClient, settings: Settings):
        self.http = http_client
        self.settings = settings
        self.base_url = settings.whatsapp_api_base_url
        self.phone_id = settings.whatsapp_phone_number_id
        self.headers = {
            "Authorization": f"Bearer {settings.whatsapp_access_token}",
            "Content-Type": "application/json",
        }

    async def send_text_message(self, to: str, text: str) -> dict | None:
        # Truncate to WhatsApp limit
        if len(text) > WHATSAPP_MAX_MESSAGE_LENGTH:
            text = text[:WHATSAPP_MAX_MESSAGE_LENGTH - 3] + "..."

        url = f"{self.base_url}/{self.phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }

        for attempt in range(MAX_RETRIES):
            try:
                response = await self.http.post(
                    url,
                    json=payload,
                    headers=self.headers,
                )
                response.raise_for_status()
                logger.info("Message sent to %s (attempt %d)", to, attempt + 1)
                return response.json()
            except httpx.HTTPStatusError as e:
                error_text = e.response.text
                logger.error(
                    "WhatsApp API error (attempt %d/%d): %s - %s",
                    attempt + 1, MAX_RETRIES,
                    e.response.status_code, error_text,
                )
                # Detect 24h window error — don't retry, raise immediately
                if any(code in error_text for code in _24H_ERROR_CODES):
                    raise WhatsApp24hWindowError(f"24h conversation window expired for {to}")
                if attempt == MAX_RETRIES - 1:
                    raise
            except httpx.RequestError as e:
                logger.error(
                    "WhatsApp request error (attempt %d/%d): %s",
                    attempt + 1,
                    MAX_RETRIES,
                    str(e),
                )
                if attempt == MAX_RETRIES - 1:
                    raise

        return None

    async def send_template_message(
        self, to: str, template_name: str, language: str = "en"
    ) -> dict | None:
        url = f"{self.base_url}/{self.phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
            },
        }

        try:
            response = await self.http.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            logger.info("Template '%s' sent to %s", template_name, to)
            return response.json()
        except Exception as e:
            logger.error("Failed to send template '%s' to %s: %s", template_name, to, e)
            return None

    async def send_feedback_buttons(self, to: str, message_id: str) -> dict | None:
        url = f"{self.base_url}/{self.phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": "Was this helpful?"},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": f"feedback_good_{message_id}",
                                "title": "Helpful",
                            },
                        },
                        {
                            "type": "reply",
                            "reply": {
                                "id": f"feedback_bad_{message_id}",
                                "title": "Not helpful",
                            },
                        },
                    ],
                },
            },
        }

        try:
            response = await self.http.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to send feedback buttons: %s", e)
            return None

    async def send_feedback_followup(self, to: str) -> dict | None:
        url = f"{self.base_url}/{self.phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": "What felt off?"},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {"id": "feedback_incorrect", "title": "Incorrect"},
                        },
                        {
                            "type": "reply",
                            "reply": {"id": "feedback_generic", "title": "Too generic"},
                        },
                        {
                            "type": "reply",
                            "reply": {"id": "feedback_other", "title": "Other"},
                        },
                    ],
                },
            },
        }

        try:
            response = await self.http.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to send feedback followup: %s", e)
            return None

    async def get_media_url(self, media_id: str) -> str:
        url = f"{self.base_url}/{media_id}"
        response = await self.http.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        return data["url"]

    async def download_media(self, media_url: str) -> bytes:
        response = await self.http.get(
            media_url,
            headers={"Authorization": f"Bearer {self.settings.whatsapp_access_token}"},
        )
        response.raise_for_status()
        return response.content
