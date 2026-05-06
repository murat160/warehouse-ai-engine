"""Runtime configuration for the AI engine.

All values are loaded from environment variables (and a local .env file in
development). Secrets MUST NOT be committed — see .env.example for the
schema.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Single source of truth for engine configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_translation_model: str = Field(
        default="gpt-4o-mini", alias="OPENAI_TRANSLATION_MODEL"
    )
    openai_stt_model: str = Field(default="whisper-1", alias="OPENAI_STT_MODEL")
    openai_tts_model: str = Field(default="tts-1", alias="OPENAI_TTS_MODEL")
    openai_tts_voice: str = Field(default="alloy", alias="OPENAI_TTS_VOICE")

    mms_tts_tuk_enabled: bool = Field(default=False, alias="MMS_TTS_TUK_ENABLED")
    mms_tts_tuk_model: str = Field(
        default="facebook/mms-tts-tuk-script_latin", alias="MMS_TTS_TUK_MODEL"
    )

    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_reload: bool = Field(default=False, alias="API_RELOAD")
    api_cors_origins: str = Field(default="*", alias="API_CORS_ORIGINS")

    translator_use_glossary: bool = Field(default=True, alias="TRANSLATOR_USE_GLOSSARY")
    translator_quality_check: bool = Field(
        default=True, alias="TRANSLATOR_QUALITY_CHECK"
    )
    translator_latency_budget: float = Field(
        default=0.3, alias="TRANSLATOR_LATENCY_BUDGET"
    )

    ffmpeg_binary: Optional[str] = Field(default=None, alias="FFMPEG_BINARY")

    @property
    def cors_origin_list(self) -> List[str]:
        if self.api_cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
