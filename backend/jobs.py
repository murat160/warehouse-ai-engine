"""Murat AI Studio — менеджер jobs (in-memory).

На VPS можно подменить на Postgres / Redis. Хранит state каждой задачи
обработки: ссылка/файл → готовое туркменское видео.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


STAGES = [
    "queued",
    "downloading",
    "extracting_audio",
    "transcribing",
    "detecting_speakers",
    "analyzing_emotions",
    "translating",
    "quality_check",
    "tts",
    "syncing",
    "rendering",
    "done",
    "failed",
]


@dataclass
class Job:
    id: str
    url: str = ""
    upload_path: str = ""
    target_lang: str = "tk"
    quality: str = "1080p"
    aspect: str = "16:9"
    voice_mode: str = "auto"          # auto / male / female / custom
    voice_profile_id: Optional[str] = None
    emotion_mode: str = "auto"        # auto / manual:<emotion>
    style: str = "cultural"
    stage: str = "queued"
    progress: int = 0                  # 0..100
    message: str = ""
    error: str = ""
    result: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "stage": self.stage,
            "progress": self.progress,
            "message": self.message,
            "error": self.error,
            "quality": self.quality,
            "aspect": self.aspect,
            "target_lang": self.target_lang,
            "result": self.result,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class JobStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._jobs: Dict[str, Job] = {}

    def create(self, **fields: Any) -> Job:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job = Job(id=job_id, **fields)
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **fields: Any) -> Optional[Job]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            for k, v in fields.items():
                if hasattr(job, k):
                    setattr(job, k, v)
            job.updated_at = time.time()
            return job

    def list(self, limit: int = 50) -> List[Job]:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
            return jobs[:limit]


STORE = JobStore()
