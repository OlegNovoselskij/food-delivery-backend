from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app import config
from app.models.catalog import Course, Lesson, LessonMaterial, Module


def get_material(db: Session, material_id: int) -> LessonMaterial | None:
    return (
        db.query(LessonMaterial)
        .options(joinedload(LessonMaterial.lesson).joinedload(Lesson.module).joinedload(Module.course))
        .filter(LessonMaterial.id == material_id)
        .first()
    )


def get_material_by_key(db: Session, file_key: str) -> LessonMaterial | None:
    return db.query(LessonMaterial).filter(LessonMaterial.file_key == file_key).first()


def add_material(db: Session, material: LessonMaterial) -> LessonMaterial:
    db.add(material)
    db.flush()
    return material


def delete_material(db: Session, material: LessonMaterial) -> None:
    db.delete(material)


def storage_keys(
    db: Session,
    *,
    course_id: int | None = None,
    module_id: int | None = None,
    lesson_id: int | None = None,
) -> list[str]:
    conditions = []
    if course_id is not None:
        conditions.append(Module.course_id == course_id)
    if module_id is not None:
        conditions.append(Lesson.module_id == module_id)
    if lesson_id is not None:
        conditions.append(Lesson.id == lesson_id)

    videos = (
        db.query(Lesson.video_key)
        .join(Module, Lesson.module_id == Module.id)
        .filter(Lesson.video_key.isnot(None), *conditions)
        .all()
    )
    files = (
        db.query(LessonMaterial.file_key)
        .join(Lesson, LessonMaterial.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .filter(*conditions)
        .all()
    )
    return [key for (key,) in videos] + [key for (key,) in files]


def used_storage_bytes(db: Session) -> int:
    # covers are charged at their maximum size: their real size is not stored
    videos = db.query(func.coalesce(func.sum(Lesson.video_size), 0)).scalar()
    materials = db.query(func.coalesce(func.sum(LessonMaterial.size_bytes), 0)).scalar()
    covers = db.query(func.count(Course.id)).filter(Course.cover_key.isnot(None)).scalar()
    return int(videos) + int(materials) + covers * config.COVER_MAX_BYTES


def referenced_storage_keys(db: Session) -> set[str]:
    videos = db.query(Lesson.video_key).filter(Lesson.video_key.isnot(None)).all()
    files = db.query(LessonMaterial.file_key).all()
    covers = db.query(Course.cover_key).filter(Course.cover_key.isnot(None)).all()
    return {key for (key,) in videos + files + covers}
