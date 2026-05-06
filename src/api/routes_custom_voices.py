"""Custom Voice API: CRUD + sample upload + preview synthesis.

Audio sample files never leave the server's local ``data/custom_voices/``
directory; this API only stores their path. Creating a profile without
``consent_given=True`` is rejected with HTTP 400.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response

from ..providers.base import ProviderError, ProviderUnavailableError
from ..speech.text_to_speech import TextToSpeech
from ..storage.repositories import (
    ConsentRequiredError,
    CustomVoiceRepository,
)
from ..voices import (
    ALLOWED_AUDIO_SUFFIXES,
    CustomVoiceError,
    CustomVoiceService,
)
from .schemas import (
    CustomVoiceCreateRequest,
    CustomVoicePreviewRequest,
    CustomVoiceSchema,
    CustomVoiceUpdateRequest,
)


def build_router(
    repository: CustomVoiceRepository,
    service: CustomVoiceService,
    *,
    tts: Optional[TextToSpeech] = None,
) -> APIRouter:
    router = APIRouter(prefix="/v1/custom-voices", tags=["custom-voices"])

    @router.get("", response_model=List[CustomVoiceSchema])
    def list_voices(
        language: Optional[str] = Query(default=None),
        channel_id: Optional[str] = Query(default=None),
        parent_id: Optional[str] = Query(default=None),
        q: Optional[str] = Query(default=None, alias="q"),
        limit: int = Query(default=200, ge=1, le=1000),
    ) -> List[CustomVoiceSchema]:
        kwargs = {"language": language, "query": q, "limit": limit}
        if channel_id == "__global__":
            kwargs["channel_id"] = None
        elif channel_id:
            kwargs["channel_id"] = channel_id
        if parent_id == "__none__":
            kwargs["parent_id"] = None
        elif parent_id:
            kwargs["parent_id"] = parent_id
        return [CustomVoiceSchema(**v.__dict__) for v in repository.list(**kwargs)]

    @router.post("", response_model=CustomVoiceSchema, status_code=201)
    def create(req: CustomVoiceCreateRequest) -> CustomVoiceSchema:
        try:
            entry = service.create(
                name=req.name,
                consent_given=req.consent_given,
                description=req.description,
                language=req.language,
                speed=req.speed,
                pitch=req.pitch,
                emotion=req.emotion,
                clarity=req.clarity,
                intensity=req.intensity,
                use_case=req.use_case,
                parent_id=req.parent_id,
                channel_id=req.channel_id,
                bound_style=req.bound_style,
                bound_video_use_case=req.bound_video_use_case,
            )
        except ConsentRequiredError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return CustomVoiceSchema(**entry.__dict__)

    @router.get("/{voice_id}", response_model=CustomVoiceSchema)
    def get(voice_id: str) -> CustomVoiceSchema:
        entry = repository.get(voice_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="custom voice not found")
        return CustomVoiceSchema(**entry.__dict__)

    @router.patch("/{voice_id}", response_model=CustomVoiceSchema)
    def update(voice_id: str, req: CustomVoiceUpdateRequest) -> CustomVoiceSchema:
        kwargs = req.model_dump(exclude_unset=True)
        entry = repository.update(voice_id, **kwargs)
        if entry is None:
            raise HTTPException(status_code=404, detail="custom voice not found")
        return CustomVoiceSchema(**entry.__dict__)

    @router.delete("/{voice_id}", status_code=204)
    def delete(voice_id: str) -> None:
        if not service.delete(voice_id):
            raise HTTPException(status_code=404, detail="custom voice not found")

    @router.post("/{voice_id}/sample", response_model=CustomVoiceSchema)
    async def upload_sample(
        voice_id: str,
        audio: UploadFile = File(...),
    ) -> CustomVoiceSchema:
        existing = repository.get(voice_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="custom voice not found")
        try:
            data = await audio.read()
            saved = service.save_sample(content=data, filename=audio.filename or "sample.wav")
        except CustomVoiceError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        # Replace any previous sample
        if existing.sample_path:
            service.delete_sample(existing.sample_path)
        updated = repository.update(voice_id, sample_path=str(saved))
        return CustomVoiceSchema(**updated.__dict__)

    @router.post("/{voice_id}/preview")
    def preview(voice_id: str, req: CustomVoicePreviewRequest) -> Response:
        existing = repository.get(voice_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="custom voice not found")
        if tts is None:
            raise HTTPException(
                status_code=503,
                detail=(
                    "TTS provider is not wired in this deployment. "
                    "Set OPENAI_API_KEY (for ru/tr/en) or enable MMS_TTS_TUK_ENABLED "
                    "(for tk) to render previews."
                ),
            )
        target_voice = service.closest_catalog_voice(existing)
        backend_voice = target_voice.backend_voice if target_voice else None
        emotion = req.emotion or existing.emotion
        try:
            out = tts.synthesize(
                req.text,
                language=existing.language,
                voice=backend_voice,
            )
        except ProviderUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        except ProviderError as exc:
            raise HTTPException(status_code=502, detail=str(exc))
        media_type = "audio/wav" if out.format == "wav" else f"audio/{out.format}"
        return Response(content=out.audio, media_type=media_type)

    return router


__all__ = ["build_router", "ALLOWED_AUDIO_SUFFIXES"]
