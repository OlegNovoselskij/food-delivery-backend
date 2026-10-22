import redis
from redis.exceptions import ConnectionError as RedisConnectionError

from app import config, redis_client, security
from app.services import storage_quota
from tests.helpers import API, auth, build_course
from tests.integration.test_media import confirm, confirm_cover, request_cover, request_upload

QUOTA_MESSAGE = "Storage limit reached. Please contact the administrator"


def lesson_ids(client, teacher, category):
    return build_course(client, teacher, category.id)["lesson_ids"]


def test_a_request_beyond_the_quota_is_refused(client, monkeypatch, teacher, category):
    monkeypatch.setattr(config, "STORAGE_QUOTA_BYTES", 1500)
    first, second = lesson_ids(client, teacher, category)
    assert request_upload(client, teacher, first).status_code == 200
    refused = request_upload(client, teacher, second)
    assert refused.status_code == 507 and refused.json()["detail"] == QUOTA_MESSAGE


def test_the_declared_size_is_signed_into_the_upload_url(client, storage, teacher, category):
    first = lesson_ids(client, teacher, category)[0]
    ticket = request_upload(client, teacher, first).json()["upload_ticket"]
    assert storage.signed_sizes[security.decode_upload_ticket(ticket)["key"]] == 1000


def test_confirming_releases_the_reservation_and_counts_the_file(client, storage, monkeypatch, fake_valkey, teacher, category):
    monkeypatch.setattr(config, "STORAGE_QUOTA_BYTES", 2500)
    first, second, *_ = lesson_ids(client, teacher, category)
    ticket = request_upload(client, teacher, first).json()["upload_ticket"]
    assert fake_valkey.zcard(storage_quota.RESERVATIONS_KEY) == 1

    storage.put(security.decode_upload_ticket(ticket)["key"], 1000, "video/mp4")
    assert confirm(client, teacher, first, ticket).status_code == 200
    assert fake_valkey.zcard(storage_quota.RESERVATIONS_KEY) == 0

    assert request_upload(client, teacher, second).status_code == 200
    assert request_upload(client, teacher, first).status_code == 200
    assert request_upload(client, teacher, second).status_code == 507


def test_a_replaced_video_does_not_count_twice(client, storage, monkeypatch, teacher, category):
    monkeypatch.setattr(config, "STORAGE_QUOTA_BYTES", 1200)
    first = lesson_ids(client, teacher, category)[0]
    for _ in range(2):
        ticket = request_upload(client, teacher, first).json()["upload_ticket"]
        storage.put(security.decode_upload_ticket(ticket)["key"], 1000, "video/mp4")
        assert confirm(client, teacher, first, ticket).status_code == 200


def test_expired_reservations_are_ignored(client, monkeypatch, fake_valkey, teacher, category):
    monkeypatch.setattr(config, "STORAGE_QUOTA_BYTES", 1500)
    fake_valkey.zadd(storage_quota.RESERVATIONS_KEY, {"1000|courses/9/lessons/9/video/old.mp4": 1})
    first = lesson_ids(client, teacher, category)[0]
    assert request_upload(client, teacher, first).status_code == 200


def test_confirm_checks_the_quota_again_and_removes_the_file(
    client, storage, monkeypatch, fake_valkey, teacher, category
):
    first = lesson_ids(client, teacher, category)[0]
    ticket = request_upload(client, teacher, first).json()["upload_ticket"]
    key = security.decode_upload_ticket(ticket)["key"]
    storage.put(key, 1000, "video/mp4")

    monkeypatch.setattr(config, "STORAGE_QUOTA_BYTES", 500)
    refused = confirm(client, teacher, first, ticket)
    assert refused.status_code == 507 and refused.json()["detail"] == QUOTA_MESSAGE
    assert key not in storage.objects
    assert fake_valkey.zcard(storage_quota.RESERVATIONS_KEY) == 0


def test_a_rejected_file_releases_its_reservation(client, storage, fake_valkey, teacher, category):
    first = lesson_ids(client, teacher, category)[0]
    ticket = request_upload(client, teacher, first).json()["upload_ticket"]
    storage.put(security.decode_upload_ticket(ticket)["key"], 1000, "text/html")
    assert confirm(client, teacher, first, ticket).status_code == 422
    assert fake_valkey.zcard(storage_quota.RESERVATIONS_KEY) == 0


def test_a_cover_counts_at_its_maximum_size(client, monkeypatch, teacher, category):
    course_id = build_course(client, teacher, category.id)["course_id"]
    monkeypatch.setattr(config, "STORAGE_QUOTA_BYTES", config.COVER_MAX_BYTES - 1)
    assert request_cover(client, teacher, course_id).status_code == 507


def test_replacing_a_cover_needs_no_extra_room(client, storage, monkeypatch, teacher, category):
    course_id = build_course(client, teacher, category.id)["course_id"]
    monkeypatch.setattr(config, "STORAGE_QUOTA_BYTES", config.COVER_MAX_BYTES)
    for _ in range(2):
        ticket = request_cover(client, teacher, course_id).json()["upload_ticket"]
        storage.put(security.decode_upload_ticket(ticket)["key"], 1000, "image/png")
        assert confirm_cover(client, teacher, course_id, ticket).status_code == 200


def test_uploads_still_work_when_valkey_is_down(client, monkeypatch, teacher, category):
    def broken() -> redis.Redis:
        raise RedisConnectionError("down")

    monkeypatch.setattr(redis_client, "get_redis", broken)
    first = lesson_ids(client, teacher, category)[0]
    response = client.post(
        f"{API}/lessons/{first}/video/upload-url",
        headers=auth(teacher),
        json={"filename": "intro.mp4", "content_type": "video/mp4", "size": 1000},
    )
    assert response.status_code == 200
