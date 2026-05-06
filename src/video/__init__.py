"""Video subsystem: extract audio, generate subtitles, dub video."""

from .dubbing_pipeline import DubbingPipeline, DubbingResult
from .subtitles import SubtitleEntry, build_srt, build_vtt
from .video_processor import VideoProcessor

__all__ = [
    "DubbingPipeline",
    "DubbingResult",
    "SubtitleEntry",
    "VideoProcessor",
    "build_srt",
    "build_vtt",
]
