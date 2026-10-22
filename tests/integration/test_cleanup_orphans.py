from datetime import UTC, datetime, timedelta

from app import config, security
from app.scripts import cleanup_orphans
from tests.helpers import build_course
from tests.integration.test_media import confirm, request_upload

OLD = datetime.now(UTC) - timedelta(seconds=config.STORAGE_ORPHAN_GRACE_SECONDS + 3600)
ORPHAN = "courses/1/lessons/1/video/0123456789abcdef0123456789abcdef.mp4"
YOUNG_ORPHAN = "courses/1/lessons/1/video/fedcba9876543210fedcba9876543210.mp4"


def confirmed_video(client, storage, teacher, category) -> str:
    lesson_id = build_course(client, teacher, category.id)["lesson_ids"][0]
    ticket = request_upload(client, teacher, lesson_id).json()["upload_ticket"]
    key = security.decode_upload_ticket(ticket)["key"]
    storage.put(key, 1000, "video/mp4", last_modified=OLD)
    assert confirm(client, teacher, lesson_id, ticket).status_code == 200
    return key


def test_only_old_unreferenced_objects_are_deleted(client, db, storage, teacher, category):
    kept = confirmed_video(client, storage, teacher, category)
    storage.put(ORPHAN, 500, "video/mp4", last_modified=OLD)
    storage.put(YOUNG_ORPHAN, 700, "video/mp4")

    summary = cleanup_orphans.cleanup(db, storage, dry_run=False)

    assert summary == {"found": 1, "deleted": 1, "bytes": 500}
    assert ORPHAN not in storage.objects
    assert kept in storage.objects and YOUNG_ORPHAN in storage.objects


def test_a_dry_run_deletes_nothing(client, db, storage, capsys):
    storage.put(ORPHAN, 500, "video/mp4", last_modified=OLD)

    summary = cleanup_orphans.cleanup(db, storage, dry_run=True)

    assert summary == {"found": 1, "deleted": 0, "bytes": 500}
    assert ORPHAN in storage.objects
    assert ORPHAN in capsys.readouterr().out


def test_objects_outside_the_courses_prefix_are_never_touched(db, storage):
    storage.put("backups/atrium.sql.gz", 500, "application/gzip", last_modified=OLD)
    assert cleanup_orphans.cleanup(db, storage, dry_run=False)["found"] == 0
    assert "backups/atrium.sql.gz" in storage.objects
