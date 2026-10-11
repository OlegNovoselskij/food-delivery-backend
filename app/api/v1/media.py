from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependency import get_optional_user, get_storage, limit_by_user, require_role
from app.models.user import User
from app.schemas.curriculum import LessonOut, MaterialOut
from app.schemas.media import (
    ConfirmMaterialRequest,
    ConfirmVideoRequest,
    MaterialUploadRequest,
    SignedUrl,
    UploadInstructions,
    VideoUploadRequest,
)
from app.services import media_service
from app.storage import S3Storage

router = APIRouter(tags=["media"])

staff_only = require_role("teacher", "admin")


@router.post(
    "/lessons/{lesson_id}/video/upload-url",
    response_model=UploadInstructions,
    dependencies=[Depends(limit_by_user("upload-url", limit=30, window_seconds=3600))],
)
def video_upload_url(
    lesson_id: int,
    data: VideoUploadRequest,
    user: User = Depends(staff_only),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
):
    return media_service.request_upload(db, lesson_id, user, media_service.VIDEO, data, storage)


@router.post("/lessons/{lesson_id}/video/confirm", response_model=LessonOut)
def confirm_video(
    lesson_id: int,
    data: ConfirmVideoRequest,
    user: User = Depends(staff_only),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
):
    return media_service.confirm_video(db, lesson_id, user, data.upload_ticket, storage)


@router.delete("/lessons/{lesson_id}/video", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(
    lesson_id: int,
    user: User = Depends(staff_only),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
):
    media_service.delete_video(db, lesson_id, user, storage)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/lessons/{lesson_id}/video-url", response_model=SignedUrl)
def video_url(
    lesson_id: int,
    viewer: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
):
    return media_service.get_video_url(db, lesson_id, viewer, storage)


@router.post(
    "/lessons/{lesson_id}/materials/upload-url",
    response_model=UploadInstructions,
    dependencies=[Depends(limit_by_user("upload-url", limit=30, window_seconds=3600))],
)
def material_upload_url(
    lesson_id: int,
    data: MaterialUploadRequest,
    user: User = Depends(staff_only),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
):
    return media_service.request_upload(db, lesson_id, user, media_service.MATERIAL, data, storage)


@router.post("/lessons/{lesson_id}/materials/confirm", response_model=MaterialOut, status_code=status.HTTP_201_CREATED)
def confirm_material(
    lesson_id: int,
    data: ConfirmMaterialRequest,
    user: User = Depends(staff_only),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
):
    return media_service.confirm_material(db, lesson_id, user, data.upload_ticket, data.title, storage)


@router.delete("/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(
    material_id: int,
    user: User = Depends(staff_only),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
):
    media_service.delete_material(db, material_id, user, storage)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/materials/{material_id}/download-url", response_model=SignedUrl)
def material_download_url(
    material_id: int,
    viewer: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
):
    return media_service.get_material_url(db, material_id, viewer, storage)
