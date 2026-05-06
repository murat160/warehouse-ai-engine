"""FastAPI integration tests using fake providers."""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from src.api.main import build_app  # noqa: E402
from src.speech.speech_to_text import SpeechToText  # noqa: E402
from src.speech.text_to_speech import TextToSpeech  # noqa: E402
from src.translator.translator_service import TranslatorService  # noqa: E402


@pytest.fixture
def client(fake_provider, fake_stt, fake_tts):
    translator = TranslatorService(primary=fake_provider, latency_budget=10.0)
    stt = SpeechToText(fake_stt)
    tts = TextToSpeech(primary=fake_tts)
    app = build_app(translator=translator, stt=stt, tts=tts)
    return TestClient(app)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert set(body["languages"]) == {"ru", "tk", "tr", "en"}


def test_translate_happy_path(client):
    resp = client.post(
        "/v1/translate",
        json={"text": "Спасибо", "source_lang": "ru", "target_lang": "tk"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["target_lang"] == "tk"
    assert body["text"]


def test_translate_rejects_unsupported_language(client):
    resp = client.post(
        "/v1/translate",
        json={"text": "hello", "source_lang": "klingon", "target_lang": "ru"},
    )
    assert resp.status_code == 400


def test_tts_returns_audio_bytes(client):
    resp = client.post(
        "/v1/tts",
        json={"text": "Salam", "language": "tk"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("audio/")
    assert resp.content.startswith(b"RIFF")


def test_stt_endpoint(client):
    resp = client.post(
        "/v1/stt",
        files={"audio": ("clip.wav", b"FAKE", "audio/wav")},
        data={"language": "ru", "with_segments": "true"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["text"]
    assert body["language"] == "ru"
    assert len(body["segments"]) == 2
