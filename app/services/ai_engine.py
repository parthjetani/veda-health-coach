import asyncio
import logging

from google import genai
from google.genai import types

from app.config import Settings
from app.core.errors import GeminiTimeoutError

logger = logging.getLogger(__name__)


class AIEngine:
    def __init__(
        self,
        client: genai.Client,
        settings: Settings,
        base_system_prompt: str,
    ):
        self.client = client
        self.model = settings.gemini_model
        self.max_tokens = settings.gemini_max_tokens
        self.temperature = settings.gemini_temperature
        self.timeout_sec = settings.gemini_timeout_sec
        self.base_system_prompt = base_system_prompt

    def _build_system_prompt(
        self,
        product_context: str | None = None,
        source_context: str | None = None,
    ) -> str:
        prompt = self.base_system_prompt

        if product_context:
            prompt += f"\n\n<product_context>\n{product_context}\n</product_context>"

        if source_context:
            prompt += f"\n\n<source_context>\n{source_context}\n</source_context>"

        return prompt

    @staticmethod
    def _validate_history(history: list[dict]) -> list[types.Content]:
        if not history:
            return []

        validated = []
        last_role = None

        for msg in history:
            role = msg.get("role")
            text = msg.get("message_text", "").strip()
            if not text or role not in ("user", "assistant"):
                continue

            # Gemini uses "model" instead of "assistant"
            gemini_role = "model" if role == "assistant" else "user"

            # Merge consecutive same-role messages
            if gemini_role == last_role and validated:
                existing_text = validated[-1].parts[0].text
                validated[-1] = types.Content(
                    role=gemini_role,
                    parts=[types.Part.from_text(text=existing_text + "\n" + text)],
                )
            else:
                validated.append(
                    types.Content(
                        role=gemini_role,
                        parts=[types.Part.from_text(text=text)],
                    )
                )
                last_role = gemini_role

        # Gemini requires the first message to be from user
        if validated and validated[0].role != "user":
            validated = validated[1:]

        return validated

    def _build_user_parts(
        self,
        user_message: str,
        image_base64: str | None = None,
        image_mime_type: str | None = None,
    ) -> list[types.Part]:
        parts = []

        if image_base64:
            import base64
            image_bytes = base64.b64decode(image_base64)
            parts.append(
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=image_mime_type or "image/jpeg",
                )
            )

        parts.append(
            types.Part.from_text(text=user_message or "Please analyze this product label.")
        )

        return parts

    async def get_response(
        self,
        user_message: str,
        conversation_history: list[dict],
        product_context: str | None = None,
        source_context: str | None = None,
        image_base64: str | None = None,
        image_mime_type: str | None = None,
    ) -> str:
        system_prompt = self._build_system_prompt(product_context, source_context)
        history = self._validate_history(conversation_history)
        user_parts = self._build_user_parts(
            user_message, image_base64, image_mime_type
        )

        # Build contents: history + current user message
        contents = history + [
            types.Content(role="user", parts=user_parts)
        ]

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=self.max_tokens,
            temperature=self.temperature,
            response_mime_type="application/json",
            response_schema={
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["product_check", "general_advice", "habit_advice", "unclear"]},
                    "verdict": {"type": "string", "enum": ["Safe", "Use with caution", "Avoid"], "nullable": True},
                    "summary": {"type": "string"},
                    "key_ingredients": {"type": "array", "items": {"type": "string"}},
                    "explanation": {"type": "string", "nullable": True},
                    "suggestion": {"type": "string", "nullable": True},
                    "follow_up": {"type": "string", "nullable": True},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                },
                "required": ["type", "summary", "key_ingredients", "confidence"],
            },
        )

        # Attempt with timeout + 1 retry
        for attempt in range(2):
            try:
                response = await asyncio.wait_for(
                    self.client.aio.models.generate_content(
                        model=self.model,
                        contents=contents,
                        config=config,
                    ),
                    timeout=self.timeout_sec,
                )

                raw_text = response.text
                logger.info(
                    "Gemini response received (attempt %d) - %d tokens (in: %d, out: %d)",
                    attempt + 1,
                    (response.usage_metadata.prompt_token_count or 0)
                    + (response.usage_metadata.candidates_token_count or 0),
                    response.usage_metadata.prompt_token_count or 0,
                    response.usage_metadata.candidates_token_count or 0,
                )
                return raw_text

            except asyncio.TimeoutError:
                logger.warning("Gemini timeout (attempt %d/%d, %ds)", attempt + 1, 2, self.timeout_sec)
                if attempt == 1:
                    raise GeminiTimeoutError(f"Gemini timed out after 2 attempts ({self.timeout_sec}s each)")
            except Exception as e:
                logger.exception("Gemini API error (attempt %d): %s", attempt + 1, e)
                if attempt == 1:
                    raise
