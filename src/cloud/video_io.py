"""Video I/O helpers: download from URL (yt-dlp) and extract mono 16k WAV."""

from __future__ import annotations

import logging
import shutil
import subprocess
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

TMP = Path("tmp")
TMP.mkdir(exist_ok=True)


class VideoDownloadError(RuntimeError):
    """Raised when yt-dlp could not produce a usable file."""


def _check_binary(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(
            f"{name!r} not found in PATH; install it (Streamlit Cloud: add to packages.txt)"
        )


def download_video(url: str) -> Path:
    """Download ``url`` via yt-dlp and return the path to the resulting file."""
    _check_binary("yt-dlp")
    job_id = uuid.uuid4().hex
    template = str(TMP / f"{job_id}.%(ext)s")
    cmd = [
        "yt-dlp",
        "-f", "best[ext=mp4]/best",
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        "-o", template,
        url,
    ]
    logger.debug("yt-dlp %s", " ".join(cmd))
    subprocess.run(cmd, check=True)
    files = sorted(TMP.glob(f"{job_id}.*"))
    if not files:
        raise VideoDownloadError(f"no file produced for {url!r}")
    return files[-1]


def extract_wav(video_path: Path, *, sample_rate: int = 16000) -> Path:
    """Extract a mono 16-bit PCM WAV track from ``video_path`` for ASR."""
    _check_binary("ffmpeg")
    video_path = Path(video_path)
    wav = TMP / f"{video_path.stem}.wav"
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ac", "1",
        "-ar", str(sample_rate),
        str(wav),
    ]
    subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return wav
