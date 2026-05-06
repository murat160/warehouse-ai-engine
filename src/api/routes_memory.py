"""CRUD + search routes for the translation memory."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..storage.repositories import TranslationMemoryRepository
from ..translator.languages import UnsupportedLanguageError, normalize_language
from .schemas import TMCreateRequest, TMEntrySchema, TMUpdateRequest


def build_router(repository: TranslationMemoryRepository) -> APIRouter:
    router = APIRouter(prefix="/v1/memory", tags=["translation-memory"])

    @router.get("", response_model=List[TMEntrySchema])
    def list_entries(
        source_lang: Optional[str] = Query(default=None),
        target_lang: Optional[str] = Query(default=None),
        q: Optional[str] = Query(default=None),
        channel_id: Optional[str] = Query(
            default=None,
            description="Set to '__global__' to fetch global-only entries.",
        ),
        limit: int = Query(default=200, ge=1, le=1000),
    ) -> List[TMEntrySchema]:
        try:
            src = normalize_language(source_lang) if source_lang else None
            tgt = normalize_language(target_lang) if target_lang else None
        except UnsupportedLanguageError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        kwargs = {"source_lang": src, "target_lang": tgt, "query": q, "limit": limit}
        if channel_id == "__global__":
            kwargs["channel_id"] = None
        elif channel_id:
            kwargs["channel_id"] = channel_id
        entries = repository.list(**kwargs)
        return [TMEntrySchema(**e.__dict__) for e in entries]

    @router.post("", response_model=TMEntrySchema, status_code=201)
    def upsert(req: TMCreateRequest) -> TMEntrySchema:
        try:
            src = normalize_language(req.source_lang)
            tgt = normalize_language(req.target_lang)
        except UnsupportedLanguageError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        try:
            entry = repository.upsert(
                source_lang=src,
                target_lang=tgt,
                source_text=req.source_text,
                target_text=req.target_text,
                score=req.score,
                note=req.note,
                channel_id=req.channel_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return TMEntrySchema(**entry.__dict__)

    @router.get("/{entry_id}", response_model=TMEntrySchema)
    def get_one(entry_id: str) -> TMEntrySchema:
        entry = repository.get(entry_id)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"tm entry {entry_id} not found")
        return TMEntrySchema(**entry.__dict__)

    @router.patch("/{entry_id}", response_model=TMEntrySchema)
    def update(entry_id: str, req: TMUpdateRequest) -> TMEntrySchema:
        kwargs = dict(target_text=req.target_text, score=req.score, note=req.note)
        if "channel_id" in req.model_fields_set:
            kwargs["channel_id"] = req.channel_id
        entry = repository.update(entry_id, **kwargs)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"tm entry {entry_id} not found")
        return TMEntrySchema(**entry.__dict__)

    @router.delete("/{entry_id}", status_code=204)
    def delete(entry_id: str) -> None:
        if not repository.delete(entry_id):
            raise HTTPException(status_code=404, detail=f"tm entry {entry_id} not found")

    return router
