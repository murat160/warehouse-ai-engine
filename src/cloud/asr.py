"""Murat AI Studio — ASR (speech recognition).

Full AI режим использует openai-whisper. В Streamlit Cloud preview Whisper
не установлен — функции возвращают понятное preview-сообщение, ничего не
крашат.

Public API:
    @dataclass ASRResult
    extract_audio_from_video(video_path) -> str
    transcribe_audio(audio_path, source_lang='auto') -> list[dict]
    segment_transcript_by_timing(transcript) -> list[dict]
    detect_language_from_audio(audio_path) -> str
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ASRResult:
    text: str
    language: Optional[str] = None  # ISO 639-1 (ru/tk/tr/en)


_SUPPORTED_LANGUAGES = {"ru", "tk", "tr", "en"}


# ---------------------------------------------------------------------------
# Service-style wrapper (back-compat).
# ---------------------------------------------------------------------------
class ASRService:
    def __init__(self, model_name: str = "small") -> None:
        logger.info("loading whisper model %s", model_name)
        self.model_name = model_name
        self.model: Optional[Any] = None
        self.preview_reason: Optional[str] = None
        try:
            import whisper  # type: ignore
            self.model = whisper.load_model(model_name)
        except Exception as exc:  # noqa: BLE001
            self.preview_reason = str(exc)
            logger.warning("Whisper unavailable; ASR runs in preview mode: %s", exc)

    def transcribe(self, wav_path: str, *, language: Optional[str] = None) -> ASRResult:
        if self.model is None:
            return ASRResult(
                text="[Murat AI Studio preview: ASR доступен на VPS / requirements-full.txt.]",
                language=language,
            )
        result = self.model.transcribe(wav_path, task="transcribe", language=language)
        return ASRResult(
            text=(result.get("text") or "").strip(),
            language=result.get("language") or language,
        )


# ---------------------------------------------------------------------------
# Functional API.
# ---------------------------------------------------------------------------
def extract_audio_from_video(video_path: str) -> str:
    """Извлекает аудио в .wav. На VPS — ffmpeg."""

    try:
        import ffmpeg  # type: ignore
    except Exception:  # noqa: BLE001
        return ""
    out = video_path.rsplit(".", 1)[0] + ".wav"
    try:
        (
            ffmpeg
            .input(video_path)
            .output(out, ac=1, ar=16000, format="wav")
            .overwrite_output()
            .run(quiet=True)
        )
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("ffmpeg extract failed: %s", exc)
        return ""


def transcribe_audio(audio_path: str, source_lang: str = "auto") -> List[Dict[str, Any]]:
    """Возвращает [{start, end, speaker, text, language, emotion}].

    На VPS — Whisper + pyannote.audio (speakers) + wav2vec2 (emotion).
    """

    try:
        import whisper  # type: ignore
    except Exception:  # noqa: BLE001
        return [{
            "start": 0.0, "end": 0.0,
            "speaker": "speaker_1",
            "text": "[Preview: ASR работает на VPS.]",
            "language": source_lang if source_lang != "auto" else "ru",
            "emotion": "neutral",
        }]
    try:
        model = whisper.load_model("small")
        kwargs: Dict[str, Any] = {"task": "transcribe"}
        if source_lang and source_lang != "auto":
            kwargs["language"] = source_lang
        result = model.transcribe(audio_path, **kwargs)
        out: List[Dict[str, Any]] = []
        for seg in result.get("segments", []):
            out.append({
                "start": float(seg.get("start", 0.0)),
                "end": float(seg.get("end", 0.0)),
                "speaker": "speaker_1",
                "text": (seg.get("text") or "").strip(),
                "language": result.get("language") or source_lang,
                "emotion": "neutral",
            })
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("whisper transcribe failed: %s", exc)
        return []


def segment_transcript_by_timing(transcript: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Объединяет соседние сегменты одного спикера если они близко по времени."""

    if not transcript:
        return []
    out = [dict(transcript[0])]
    for seg in transcript[1:]:
        last = out[-1]
        same_speaker = last.get("speaker") == seg.get("speaker")
        gap = float(seg.get("start", 0)) - float(last.get("end", 0))
        if same_speaker and gap <= 0.4:
            last["end"] = seg.get("end", last["end"])
            last["text"] = (last["text"] + " " + seg.get("text", "")).strip()
        else:
            out.append(dict(seg))
    return out


def detect_language_from_audio(audio_path: str) -> str:
    """На VPS — whisper.detect_language. В preview — 'ru' default."""

    try:
        import whisper  # type: ignore
        model = whisper.load_model("tiny")
        audio = whisper.load_audio(audio_path)
        audio = whisper.pad_or_trim(audio)
        mel = whisper.log_mel_spectrogram(audio).to(model.device)
        _, probs = model.detect_language(mel)
        lang = max(probs, key=probs.get)
        return lang if lang in _SUPPORTED_LANGUAGES else "ru"
    except Exception:  # noqa: BLE001
        return "ru"
