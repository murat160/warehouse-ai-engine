"""ffmpeg-backed helpers for splitting and remuxing video.

This module is a thin wrapper around the system ``ffmpeg`` binary. We shell
out via ``subprocess`` instead of pulling in a heavier dependency so the
engine works in containers that already ship ffmpeg.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..config import Settings, get_settings

logger = logging.getLogger(__name__)


class FFmpegNotFoundError(RuntimeError):
    """Raised when ffmpeg is not available on the host."""


@dataclass
class VideoProcessor:
    settings: Optional[Settings] = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()

    @property
    def ffmpeg(self) -> str:
        binary = self.settings.ffmpeg_binary if self.settings else None
        return binary or shutil.which("ffmpeg") or "ffmpeg"

    def ensure_available(self) -> None:
        if shutil.which(self.ffmpeg) is None and not Path(self.ffmpeg).exists():
            raise FFmpegNotFoundError(
                f"ffmpeg binary not found at {self.ffmpeg!r}; install ffmpeg or set FFMPEG_BINARY"
            )

    def extract_audio(self, video_path: Path, audio_path: Path, *, sample_rate: int = 16000) -> Path:
        """Extract a mono PCM WAV track from ``video_path`` for STT."""
        self.ensure_available()
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            self.ffmpeg, "-y", "-i", str(video_path),
            "-vn", "-acodec", "pcm_s16le",
            "-ac", "1", "-ar", str(sample_rate),
            str(audio_path),
        ]
        logger.debug("ffmpeg extract_audio: %s", " ".join(cmd))
        subprocess.run(cmd, check=True, capture_output=True)
        return audio_path

    def replace_audio(
        self,
        video_path: Path,
        new_audio_path: Path,
        output_path: Path,
        *,
        keep_original_volume: float = 0.0,
    ) -> Path:
        """Mux ``new_audio_path`` onto ``video_path``.

        ``keep_original_volume`` mixes the original track at the given linear
        volume — useful for partial dubbing where the source ambience is kept.
        """
        self.ensure_available()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if keep_original_volume <= 0:
            cmd = [
                self.ffmpeg, "-y",
                "-i", str(video_path),
                "-i", str(new_audio_path),
                "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0",
                "-shortest",
                str(output_path),
            ]
        else:
            mix = (
                f"[0:a]volume={keep_original_volume}[a0];"
                "[1:a]volume=1.0[a1];"
                "[a0][a1]amix=inputs=2:duration=longest[a]"
            )
            cmd = [
                self.ffmpeg, "-y",
                "-i", str(video_path),
                "-i", str(new_audio_path),
                "-filter_complex", mix,
                "-map", "0:v:0", "-map", "[a]",
                "-c:v", "copy",
                str(output_path),
            ]
        logger.debug("ffmpeg replace_audio: %s", " ".join(cmd))
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
