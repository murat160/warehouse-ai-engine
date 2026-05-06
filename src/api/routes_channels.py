"""CRUD routes for channels (AI agents)."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException

from ..storage.repositories import ChannelRepository, DuplicateEntryError
from .schemas import ChannelCreateRequest, ChannelSchema, ChannelUpdateRequest


def build_router(repository: ChannelRepository) -> APIRouter:
    router = APIRouter(prefix="/v1/channels", tags=["channels"])

    @router.get("", response_model=List[ChannelSchema])
    def list_channels(limit: int = 200) -> List[ChannelSchema]:
        return [ChannelSchema(**c.__dict__) for c in repository.list(limit=limit)]

    @router.post("", response_model=ChannelSchema, status_code=201)
    def create(req: ChannelCreateRequest) -> ChannelSchema:
        try:
            entry = repository.create(
                name=req.name,
                description=req.description,
                primary_lang=req.primary_lang,
                target_lang=req.target_lang,
                style=req.style,
                tone=req.tone,
                emotion=req.emotion,
                voice_id=req.voice_id,
                voice_use_case=req.voice_use_case,
                dubbing_notes=req.dubbing_notes,
            )
        except DuplicateEntryError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return ChannelSchema(**entry.__dict__)

    @router.get("/{channel_id}", response_model=ChannelSchema)
    def get_one(channel_id: str) -> ChannelSchema:
        entry = repository.get(channel_id)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"channel {channel_id} not found")
        return ChannelSchema(**entry.__dict__)

    @router.patch("/{channel_id}", response_model=ChannelSchema)
    def update(channel_id: str, req: ChannelUpdateRequest) -> ChannelSchema:
        entry = repository.update(
            channel_id,
            name=req.name,
            description=req.description,
            primary_lang=req.primary_lang,
            target_lang=req.target_lang,
            style=req.style,
            tone=req.tone,
            emotion=req.emotion,
            voice_id=req.voice_id,
            voice_use_case=req.voice_use_case,
            dubbing_notes=req.dubbing_notes,
        )
        if entry is None:
            raise HTTPException(status_code=404, detail=f"channel {channel_id} not found")
        return ChannelSchema(**entry.__dict__)

    @router.delete("/{channel_id}", status_code=204)
    def delete(channel_id: str) -> None:
        if not repository.delete(channel_id):
            raise HTTPException(status_code=404, detail=f"channel {channel_id} not found")

    return router
