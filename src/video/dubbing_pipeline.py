"""End-to-end video dubbing pipeline (scaffold).

Stages:
    1. extract audio with :class:`VideoProcessor`,
    2. transcribe with :class:`SpeechToText` (segments + timing),
    3. translate every segment with :class:`TranslatorService`,
    4. synthesise the translated text with :class:`TextToSpeech`,
    5. mux the new audio back onto the original video.

Each stage emits artefacts so callers can resume from a partial run; the
pipeline itself is deliberately small — heavy work lives in the dependencies.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from ..providers.base import TranscriptSegment
from ..speech.speech_to_text import SpeechToText
from ..speech.text_to_speech import TextToSpeech
from ..translator.translator_service import TranslatorService
from .subtitles import SubtitleEntry, build_srt, from_segments
from .video_processor import VideoProcessor

logger = logging.getLogger(__name__)


@dataclass
class DubbingResult:
    """Artefacts produced by a single dubbing run."""

    video_in: Path
    video_out: Path
    audio_extracted: Path
    audio_dubbed: Path
    source_subtitles: List[SubtitleEntry] = field(default_factory=list)
    target_subtitles: List[SubtitleEntry] = field(default_factory=list)
    source_lang: str = ""
    target_lang: str = ""

    def srt_source(self) -> str:
        return build_srt(self.source_subtitles)

    def srt_target(self) -> str:
        return build_srt(self.target_subtitles)


@dataclass
class DubbingPipeline:
    translator: TranslatorService
    stt: SpeechToText
    tts: TextToSpeech
    video: VideoProcessor

    def run(
        self,
        *,
        video_path: Path,
        target_lang: str,
        source_lang: Optional[str] = None,
        workdir: Optional[Path] = None,
        keep_original_volume: float = 0.0,
    ) -> DubbingResult:
        video_path = Path(video_path)
        workdir = Path(workdir or video_path.with_suffix("").as_posix() + "_dub")
        workdir.mkdir(parents=True, exist_ok=True)

        audio_in = workdir / "source.wav"
        audio_out = workdir / "dubbed.wav"
        video_out = workdir / f"{video_path.stem}.{target_lang}{video_path.suffix}"

        # 1) Extract source audio
        self.video.extract_audio(video_path, audio_in)

        # 2) Transcribe with timestamps
        stt_result = self.stt.transcribe(
            audio_in.read_bytes(),
            language_hint=source_lang,
            with_segments=True,
        )
        detected_lang = stt_result.language or source_lang or "ru"
        source_subs = from_segments(stt_result.segments)

        # 3) Translate every segment, preserving timings
        target_segments: List[TranscriptSegment] = []
        for seg in stt_result.segments:
            translated = self.translator.translate(
                text=seg.text,
                source_lang=detected_lang,
                target_lang=target_lang,
            ).text
            target_segments.append(
                TranscriptSegment(start=seg.start, end=seg.end, text=translated)
            )
        target_subs = from_segments(target_segments)

        # 4) TTS — concatenated full track. A future iteration should align
        #    each clip to its segment timing; the scaffold synthesises the
        #    whole translated transcript in one go.
        full_text = " ".join(s.text for s in target_segments).strip()
        tts_result = self.tts.synthesize(full_text, language=target_lang)
        audio_out.write_bytes(tts_result.audio)

        # 5) Mux dubbed audio back onto the source video
        self.video.replace_audio(
            video_path, audio_out, video_out,
            keep_original_volume=keep_original_volume,
        )

        return DubbingResult(
            video_in=video_path,
            video_out=video_out,
            audio_extracted=audio_in,
            audio_dubbed=audio_out,
            source_subtitles=source_subs,
            target_subtitles=target_subs,
            source_lang=detected_lang,
            target_lang=target_lang,
        )
