"""Publishing API: CRUD + media upload + ZIP export + platform list."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response

from ..publishing import PublishingService, build_zip_for_package
from ..publishing.models import list_platforms, normalize_platforms
from ..storage.repositories import PublishingRepository
from .schemas import (
    PublishingPackageCreateRequest,
    PublishingPackageSchema,
    PublishingPackageUpdateRequest,
    PublishingPlatformSchema,
)


def build_router(
    repository: PublishingRepository,
    service: PublishingService,
) -> APIRouter:
    router = APIRouter(prefix="/v1/publishing", tags=["publishing"])

    @router.get("/platforms", response_model=List[PublishingPlatformSchema])
    def platforms() -> List[PublishingPlatformSchema]:
        return [PublishingPlatformSchema(**p.to_dict()) for p in list_platforms()]

    @router.get("", response_model=List[PublishingPackageSchema])
    def list_packages(
        language: Optional[str] = Query(default=None),
        channel_id: Optional[str] = Query(default=None),
        status: Optional[str] = Query(default=None),
        platform: Optional[str] = Query(default=None),
        q: Optional[str] = Query(default=None),
        limit: int = Query(default=200, ge=1, le=1000),
    ) -> List[PublishingPackageSchema]:
        kwargs = {"language": language, "status": status, "platform": platform,
                  "query": q, "limit": limit}
        if channel_id == "__global__":
            kwargs["channel_id"] = None
        elif channel_id:
            kwargs["channel_id"] = channel_id
        return [
            PublishingPackageSchema(**p.__dict__) for p in repository.list(**kwargs)
        ]

    @router.post("", response_model=PublishingPackageSchema, status_code=201)
    def create(req: PublishingPackageCreateRequest) -> PublishingPackageSchema:
        try:
            entry = service.create(
                name=req.name,
                title=req.title,
                kind=req.kind,
                language=req.language,
                channel_id=req.channel_id,
                description=req.description,
                tags=req.tags,
                hashtags=req.hashtags,
                target_platforms=req.target_platforms,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return PublishingPackageSchema(**entry.__dict__)

    @router.get("/{package_id}", response_model=PublishingPackageSchema)
    def get(package_id: str) -> PublishingPackageSchema:
        entry = repository.get(package_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="package not found")
        return PublishingPackageSchema(**entry.__dict__)

    @router.patch("/{package_id}", response_model=PublishingPackageSchema)
    def update(
        package_id: str, req: PublishingPackageUpdateRequest,
    ) -> PublishingPackageSchema:
        kwargs = req.model_dump(exclude_unset=True)
        if "target_platforms" in kwargs and kwargs["target_platforms"] is not None:
            kwargs["target_platforms"] = normalize_platforms(kwargs["target_platforms"])
        entry = service.update(package_id, **kwargs)
        if entry is None:
            raise HTTPException(status_code=404, detail="package not found")
        return PublishingPackageSchema(**entry.__dict__)

    @router.delete("/{package_id}", status_code=204)
    def delete(package_id: str) -> None:
        if not service.delete(package_id):
            raise HTTPException(status_code=404, detail="package not found")

    @router.post("/{package_id}/media", response_model=PublishingPackageSchema)
    async def upload_media(
        package_id: str,
        media: UploadFile = File(...),
    ) -> PublishingPackageSchema:
        existing = repository.get(package_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="package not found")
        try:
            data = await media.read()
            updated = service.replace_media(
                package_id,
                content=data,
                filename=media.filename or "media.bin",
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        if updated is None:
            raise HTTPException(status_code=404, detail="package not found")
        return PublishingPackageSchema(**updated.__dict__)

    @router.get("/{package_id}/export")
    def export(package_id: str) -> Response:
        package = repository.get(package_id)
        if package is None:
            raise HTTPException(status_code=404, detail="package not found")
        archive = build_zip_for_package(package)
        service.mark_exported(package_id)
        filename = f"{package.name.replace(' ', '_') or package.id}.zip"
        return Response(
            content=archive,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
        )

    @router.post("/{package_id}/publish", response_model=PublishingPackageSchema)
    def mark_published(package_id: str) -> PublishingPackageSchema:
        updated = service.mark_published(package_id)
        if updated is None:
            raise HTTPException(status_code=404, detail="package not found")
        return PublishingPackageSchema(**updated.__dict__)

    return router


__all__ = ["build_router"]
