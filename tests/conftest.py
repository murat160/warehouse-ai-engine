"""Shared pytest fixtures and a fake translation provider used across tests."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import pytest

# Ensure the package under test is importable when running `pytest` from the
# repo root without an editable install.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.providers.base import (  # noqa: E402  -- import after sys.path tweak
    AudioBytes,
    ProviderUnavailableError,
    STTProvider,
    STTResult,
    TTSProvider,
    TTSResult,
    TranscriptSegment,
    TranslationProvider,
)


class FakeTranslationProvider(TranslationProvider):
    """Deterministic provider that prefixes the text with the target lang."""

    name = "fake"

    def __init__(self, *, available: bool = True, glossary_friendly: bool = True) -> None:
        self._available = available
        self._glossary_friendly = glossary_friendly

    def is_available(self) -> bool:  # type: ignore[override]
        return self._available

    def translate(
        self,
        *,
        text: str,
        source_lang: str,
        target_lang: str,
        literary: bool = False,
        style: Optional[str] = None,
        tone: Optional[str] = None,
        emotion: Optional[str] = None,
    ) -> str:
        if not self._available:
            raise ProviderUnavailableError("fake provider disabled")
        # Produce something that passes script checks: Cyrillic for ru,
        # Latin otherwise. Useful so quality_check does not fire false
        # positives in pure unit tests.
        if target_lang == "ru":
            sample = "перевод"
        else:
            sample = "terjime" if target_lang == "tk" else "translation"
        # Keep the original-length ratio reasonable.
        return f"{sample}: {text}"


class FakeSTTProvider(STTProvider):
    name = "fake-stt"

    def is_available(self) -> bool:  # type: ignore[override]
        return True

    def transcribe(
        self,
        audio: AudioBytes,
        *,
        language_hint: Optional[str] = None,
        with_segments: bool = False,
    ) -> STTResult:
        segments = []
        if with_segments:
            segments = [
                TranscriptSegment(start=0.0, end=1.0, text="привет"),
                TranscriptSegment(start=1.0, end=2.0, text="как дела"),
            ]
        return STTResult(
            text="привет как дела",
            language=language_hint or "ru",
            segments=segments,
            duration=2.0,
        )


class FakeTTSProvider(TTSProvider):
    name = "fake-tts"

    def __init__(self, *, supported_languages=("ru", "tk", "tr", "en")) -> None:
        self._supported = set(supported_languages)

    def is_available(self, language: str) -> bool:  # type: ignore[override]
        return language in self._supported

    def synthesize(
        self,
        text: str,
        *,
        language: str,
        voice: Optional[str] = None,
    ) -> TTSResult:
        if language not in self._supported:
            raise ProviderUnavailableError(f"fake-tts does not support {language}")
        # 16-bit PCM WAV header for an empty mono 16kHz file is 44 bytes;
        # we just return the marker bytes so tests can inspect them.
        return TTSResult(audio=b"RIFF\x00\x00\x00\x00WAVEfake", sample_rate=16000)


@pytest.fixture
def fake_provider() -> FakeTranslationProvider:
    return FakeTranslationProvider()


@pytest.fixture
def fake_stt() -> FakeSTTProvider:
    return FakeSTTProvider()


@pytest.fixture
def fake_tts() -> FakeTTSProvider:
    return FakeTTSProvider()


@pytest.fixture
def isolated_db(tmp_path):
    """Initialise a fresh SQLite database file for each test that needs one."""
    from src.storage import db as storage_db

    storage_db.reset_for_tests()
    db_file = tmp_path / "test.db"
    storage_db.init_db(f"sqlite:///{db_file.as_posix()}")
    yield db_file
    storage_db.reset_for_tests()


@pytest.fixture
def glossary_repo(isolated_db):
    from src.storage.repositories import GlossaryRepository

    return GlossaryRepository()


@pytest.fixture
def tm_repo(isolated_db):
    from src.storage.repositories import TranslationMemoryRepository

    return TranslationMemoryRepository()
