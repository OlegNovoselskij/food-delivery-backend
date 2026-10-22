import uuid

import jwt
from sqlalchemy.orm import Session

from app import config
from app.exceptions import (
    InvalidUploadedFile,
    InvalidUploadTicket,
    LessonHasNoVideo,
    MaterialNotFound,
    NotCourseOwner,
    StorageQuotaExceeded,
    UploadNotFound,
)
from app.models.catalog import Course, Lesson, LessonMaterial
from app.models.user import User
from app.patterns.observer.event_bus import event_bus
from app.patterns.observer.events import CatalogChanged
from app.repository import course_repository, curriculum_repository, media_repository
from app.security import create_upload_ticket, decode_upload_ticket
from app.services import curriculum_service, storage_quota
from app.services.access import can_manage_course, get_course_for_edit, get_lesson_for_edit
from app.storage import S3Storage

VIDEO = "video"
MATERIAL = "material"
COVER = "cover"
COVER_PUBLIC_KEYS = "courses/*/cover/*"

_RULES = {
    VIDEO: (config.VIDEO_TYPES, config.VIDEO_MAX_BYTES),
    MATERIAL: (config.MATERIAL_TYPES, config.MATERIAL_MAX_BYTES),
    COVER: (config.COVER_TYPES, config.COVER_MAX_BYTES),
}


def _new_key(course_id: int, lesson_id: int, kind: str, content_type: str) -> str:
    extension = _RULES[kind][0][content_type]
    return f"courses/{course_id}/lessons/{lesson_id}/{kind}/{uuid.uuid4().hex}{extension}"


def _read_ticket(ticket: str, user: User, kind: str, **scope: int) -> dict:
    try:
        claims = decode_upload_ticket(ticket)
    except jwt.PyJWTError:
        raise InvalidUploadTicket()
    if claims.get("uid") != user.id or claims.get("kind") != kind:
        raise InvalidUploadTicket()
    if any(claims.get(name) != value for name, value in scope.items()):
        raise InvalidUploadTicket()
    return claims


def _charge(kind: str, size: int) -> int:
    return config.COVER_MAX_BYTES if kind == COVER else size  # the cover size is not stored: it counts at the maximum


def _check_uploaded_object(storage: S3Storage, claims: dict, kind: str) -> dict:
    head = storage.head(claims["key"])
    if head is None:
        raise UploadNotFound()

    stored_type = (head["content_type"] or "").split(";")[0].strip().lower()
    if head["size"] <= 0 or head["size"] > _RULES[kind][1] or stored_type != claims["ct"]:
        storage.delete_many([claims["key"]])
        storage_quota.release(claims["key"])
        raise InvalidUploadedFile()
    return head


def _ensure_room(db: Session, storage: S3Storage, claims: dict, size: int, *, replacing: int = 0) -> None:
    try:
        storage_quota.ensure_room(db, size, replacing=replacing)
    except StorageQuotaExceeded:
        storage.delete_many([claims["key"]])
        storage_quota.release(claims["key"])
        raise


def request_upload(db: Session, lesson_id: int, user: User, kind: str, data, storage: S3Storage) -> dict:
    lesson = get_lesson_for_edit(db, lesson_id, user)
    key = _new_key(lesson.module.course_id, lesson.id, kind, data.content_type)

    storage.ensure_bucket()
    replacing = (lesson.video_size or 0) if kind == VIDEO else 0
    storage_quota.reserve(db, key, _charge(kind, data.size), replacing=replacing)
    ticket = create_upload_ticket(
        user_id=user.id,
        kind=kind,
        lesson_id=lesson.id,
        key=key,
        content_type=data.content_type,
        filename=data.filename,
    )
    return {
        "upload_url": storage.upload_url(key, data.content_type, config.UPLOAD_URL_TTL_SECONDS, size=data.size),
        "method": "PUT",
        "headers": {"Content-Type": data.content_type},
        "upload_ticket": ticket,
        "expires_in": config.UPLOAD_URL_TTL_SECONDS,
    }


def confirm_video(db: Session, lesson_id: int, user: User, ticket: str, storage: S3Storage) -> Lesson:
    lesson = get_lesson_for_edit(db, lesson_id, user)
    claims = _read_ticket(ticket, user, VIDEO, lesson_id=lesson.id)

    if lesson.video_key == claims["key"]:
        return lesson

    head = _check_uploaded_object(storage, claims, VIDEO)
    _ensure_room(db, storage, claims, head["size"], replacing=lesson.video_size or 0)
    old_key = lesson.video_key
    lesson.video_key = claims["key"]
    lesson.video_size = head["size"]
    db.commit()

    storage_quota.release(claims["key"])
    storage.delete_many([old_key])
    return curriculum_repository.get_lesson(db, lesson.id)


def delete_video(db: Session, lesson_id: int, user: User, storage: S3Storage) -> None:
    lesson = get_lesson_for_edit(db, lesson_id, user)
    if not lesson.video_key:
        raise LessonHasNoVideo()
    old_key = lesson.video_key
    lesson.video_key = None
    lesson.video_size = None
    db.commit()
    storage.delete_many([old_key])


def confirm_material(
    db: Session, lesson_id: int, user: User, ticket: str, title: str, storage: S3Storage
) -> LessonMaterial:
    lesson = get_lesson_for_edit(db, lesson_id, user)
    claims = _read_ticket(ticket, user, MATERIAL, lesson_id=lesson.id)

    existing = media_repository.get_material_by_key(db, claims["key"])
    if existing is not None:
        return existing

    head = _check_uploaded_object(storage, claims, MATERIAL)
    _ensure_room(db, storage, claims, head["size"])
    material = LessonMaterial(
        lesson_id=lesson.id,
        title=title,
        file_key=claims["key"],
        original_filename=claims["fn"],
        content_type=claims["ct"],
        size_bytes=head["size"],
    )
    media_repository.add_material(db, material)
    db.commit()
    storage_quota.release(claims["key"])
    db.refresh(material)
    return material


def delete_material(db: Session, material_id: int, user: User, storage: S3Storage) -> None:
    material = media_repository.get_material(db, material_id)
    if material is None:
        raise MaterialNotFound()
    if not can_manage_course(material.lesson.module.course, user):
        raise NotCourseOwner()
    key = material.file_key
    media_repository.delete_material(db, material)
    db.commit()
    storage.delete_many([key])


def get_video_url(db: Session, lesson_id: int, viewer: User | None, storage: S3Storage) -> dict:
    lesson = curriculum_service.get_lesson_for_viewer(db, lesson_id, viewer)
    if not lesson.video_key:
        raise LessonHasNoVideo()
    ttl = config.DOWNLOAD_URL_TTL_SECONDS
    return {"url": storage.download_url(lesson.video_key, ttl), "expires_in": ttl}


def get_material_url(db: Session, material_id: int, viewer: User | None, storage: S3Storage) -> dict:
    material = media_repository.get_material(db, material_id)
    if material is None:
        raise MaterialNotFound()
    curriculum_service.get_lesson_for_viewer(db, material.lesson_id, viewer)
    ttl = config.DOWNLOAD_URL_TTL_SECONDS
    url = storage.download_url(material.file_key, ttl, filename=material.original_filename)
    return {"url": url, "expires_in": ttl}


def request_cover_upload(db: Session, course_id: int, user: User, data, storage: S3Storage) -> dict:
    course = get_course_for_edit(db, course_id, user)
    extension = config.COVER_TYPES[data.content_type]
    key = f"courses/{course.id}/cover/{uuid.uuid4().hex}{extension}"

    storage.ensure_bucket()
    replacing = config.COVER_MAX_BYTES if course.cover_key else 0
    storage_quota.reserve(db, key, _charge(COVER, data.size), replacing=replacing)
    ticket = create_upload_ticket(
        user_id=user.id,
        kind=COVER,
        course_id=course.id,
        key=key,
        content_type=data.content_type,
        filename=data.filename,
    )
    return {
        "upload_url": storage.upload_url(key, data.content_type, config.UPLOAD_URL_TTL_SECONDS, size=data.size),
        "method": "PUT",
        "headers": {"Content-Type": data.content_type},
        "upload_ticket": ticket,
        "expires_in": config.UPLOAD_URL_TTL_SECONDS,
    }


def confirm_cover(db: Session, course_id: int, user: User, ticket: str, storage: S3Storage) -> Course:
    course = get_course_for_edit(db, course_id, user)
    claims = _read_ticket(ticket, user, COVER, course_id=course.id)

    if course.cover_key == claims["key"]:
        return course

    _check_uploaded_object(storage, claims, COVER)
    replacing = config.COVER_MAX_BYTES if course.cover_key else 0
    _ensure_room(db, storage, claims, config.COVER_MAX_BYTES, replacing=replacing)
    storage.ensure_public_read(COVER_PUBLIC_KEYS)
    old_key = course.cover_key
    course.cover_key = claims["key"]
    course.cover_url = storage.public_url(claims["key"])
    event_bus.publish(db, CatalogChanged(reason="course_updated"))
    db.commit()

    storage_quota.release(claims["key"])
    storage.delete_many([old_key])
    return course_repository.get_by_id(db, course.id)


def delete_cover(db: Session, course_id: int, user: User, storage: S3Storage) -> Course:
    course = get_course_for_edit(db, course_id, user)
    old_key = course.cover_key
    course.cover_key = None
    course.cover_url = None
    event_bus.publish(db, CatalogChanged(reason="course_updated"))
    db.commit()

    storage.delete_many([old_key])
    return course_repository.get_by_id(db, course.id)
