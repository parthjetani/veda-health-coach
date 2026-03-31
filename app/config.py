from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # WhatsApp Cloud API
    whatsapp_access_token: str
    whatsapp_phone_number_id: str
    whatsapp_verify_token: str
    whatsapp_api_version: str = "v21.0"

    # Google Gemini
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    gemini_max_tokens: int = 4096
    gemini_temperature: float = 0.3

    # Supabase
    supabase_url: str
    supabase_service_role_key: str

    # Admin
    admin_api_key: str

    # Production hardening
    gemini_timeout_sec: int = 30
    max_image_size_bytes: int = 5_000_000  # 5MB
    rate_limit_per_hour: int = 30

    # App
    environment: str = "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def whatsapp_api_base_url(self) -> str:
        return f"https://graph.facebook.com/{self.whatsapp_api_version}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
