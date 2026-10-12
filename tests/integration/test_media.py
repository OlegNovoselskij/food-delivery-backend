from app import security
from tests.helpers import API, auth, build_course, create_user


def request_upload(client, teacher, lesson_id, content_type="video/mp4"):
    return client.post(
        f"{API}/lessons/{lesson_id}/video/upload-url",
        headers=auth(teacher),
        json={"filename": "intro.mp4", "content_type": content_type, "size": 1000},
    )


def confirm(client, teacher, lesson_id, ticket):
    return client.post(
        f"{API}/lessons/{lesson_id}/video/confirm", headers=auth(teacher), json={"upload_ticket": ticket}
    )


def test_the_upload_flow_stores_a_key_not_the_filename(client, storage, teacher, category):
    lesson_id = build_course(client, teacher, category.id)["lesson_ids"][1]
    ticket = request_upload(client, teacher, lesson_id).json()["upload_ticket"]
    key = security.decode_upload_ticket(ticket)["key"]
    assert "intro" not in key

    assert confirm(client, teacher, lesson_id, ticket).status_code == 409
    storage.put(key, 1000, "video/mp4")
    confirmed = confirm(client, teacher, lesson_id, ticket)
    assert confirmed.status_code == 200 and confirmed.json()["has_video"] is True


def test_a_file_of_the_wrong_type_is_rejected_and_removed(client, storage, teacher, category):
    lesson_id = build_course(client, teacher, category.id)["lesson_ids"][1]
    ticket = request_upload(client, teacher, lesson_id).json()["upload_ticket"]
    key = security.decode_upload_ticket(ticket)["key"]
    storage.put(key, 1000, "text/html")
    assert confirm(client, teacher, lesson_id, ticket).status_code == 422
    assert key not in storage.objects


def test_unsupported_types_and_foreign_tickets_are_rejected(client, teacher, category):
    first, second = build_course(client, teacher, category.id)["lesson_ids"]
    assert request_upload(client, teacher, first, "video/avi").status_code == 422
    ticket = request_upload(client, teacher, first).json()["upload_ticket"]
    assert confirm(client, teacher, second, ticket).status_code == 400


def test_other_teachers_cannot_upload_to_the_lesson(client, db, teacher, category):
    lesson_id = build_course(client, teacher, category.id)["lesson_ids"][0]
    other = create_user(db, "teacher", email="other@example.com")
    assert request_upload(client, other, lesson_id).status_code == 403


def test_video_links_follow_the_lesson_access_rules(client, storage, teacher, student, category):
    course = build_course(client, teacher, category.id)
    lesson_id = course["lesson_ids"][1]
    ticket = request_upload(client, teacher, lesson_id).json()["upload_ticket"]
    storage.put(security.decode_upload_ticket(ticket)["key"], 1000, "video/mp4")
    confirm(client, teacher, lesson_id, ticket)

    url = f"{API}/lessons/{lesson_id}/video-url"
    assert client.get(url).status_code == 403
    assert client.get(url, headers=auth(student)).status_code == 403
    client.post(f"{API}/courses/{course['course_id']}/enroll", headers=auth(student))
    link = client.get(url, headers=auth(student))
    assert link.status_code == 200 and link.json()["url"].startswith("https://storage.test/download/")


def test_deleting_a_lesson_removes_its_files(client, storage, teacher, category):
    lesson_id = build_course(client, teacher, category.id)["lesson_ids"][1]
    ticket = request_upload(client, teacher, lesson_id).json()["upload_ticket"]
    key = security.decode_upload_ticket(ticket)["key"]
    storage.put(key, 1000, "video/mp4")
    confirm(client, teacher, lesson_id, ticket)
    assert client.delete(f"{API}/lessons/{lesson_id}", headers=auth(teacher)).status_code == 204
    assert key not in storage.objects


def request_cover(client, user, course_id, content_type="image/png", size=1000):
    return client.post(
        f"{API}/courses/{course_id}/cover/upload-url",
        headers=auth(user),
        json={"filename": "cover.png", "content_type": content_type, "size": size},
    )


def confirm_cover(client, user, course_id, ticket):
    return client.post(f"{API}/courses/{course_id}/cover/confirm", headers=auth(user), json={"upload_ticket": ticket})


def test_the_cover_flow_publishes_a_public_url(client, storage, teacher, category):
    course_id = build_course(client, teacher, category.id)["course_id"]
    ticket = request_cover(client, teacher, course_id).json()["upload_ticket"]
    key = security.decode_upload_ticket(ticket)["key"]
    assert key.startswith(f"courses/{course_id}/cover/") and "cover.png" not in key

    assert confirm_cover(client, teacher, course_id, ticket).status_code == 409
    storage.put(key, 1000, "image/png")
    confirmed = confirm_cover(client, teacher, course_id, ticket)
    assert confirmed.status_code == 200
    assert confirmed.json()["cover_url"] == f"https://storage.test/public/{key}"


def test_replacing_and_removing_a_cover_deletes_the_old_file(client, storage, teacher, category):
    course_id = build_course(client, teacher, category.id)["course_id"]
    keys = []
    for _ in range(2):
        ticket = request_cover(client, teacher, course_id).json()["upload_ticket"]
        key = security.decode_upload_ticket(ticket)["key"]
        storage.put(key, 1000, "image/png")
        confirm_cover(client, teacher, course_id, ticket)
        keys.append(key)
    assert keys[0] not in storage.objects and keys[1] in storage.objects

    removed = client.delete(f"{API}/courses/{course_id}/cover", headers=auth(teacher))
    assert removed.status_code == 200 and removed.json()["cover_url"] is None
    assert keys[1] not in storage.objects


def test_cover_types_sizes_and_owners_are_checked(client, storage, db, teacher, category):
    course_id = build_course(client, teacher, category.id)["course_id"]
    assert request_cover(client, teacher, course_id, "image/svg+xml").status_code == 422
    assert request_cover(client, teacher, course_id, size=6 * 1024**2).status_code == 422
    other = create_user(db, "teacher", email="other@example.com")
    assert request_cover(client, other, course_id).status_code == 403

    ticket = request_cover(client, teacher, course_id).json()["upload_ticket"]
    key = security.decode_upload_ticket(ticket)["key"]
    storage.put(key, 1000, "text/html")
    assert confirm_cover(client, teacher, course_id, ticket).status_code == 422
    assert key not in storage.objects


def test_a_cover_ticket_is_bound_to_its_course(client, storage, teacher, category):
    first = build_course(client, teacher, category.id)["course_id"]
    second = build_course(client, teacher, category.id, title="Second course")["course_id"]
    ticket = request_cover(client, teacher, first).json()["upload_ticket"]
    storage.put(security.decode_upload_ticket(ticket)["key"], 1000, "image/png")
    assert confirm_cover(client, teacher, second, ticket).status_code == 400


def test_deleting_a_course_removes_its_cover(client, storage, teacher, category):
    course_id = build_course(client, teacher, category.id, publish=False)["course_id"]
    ticket = request_cover(client, teacher, course_id).json()["upload_ticket"]
    key = security.decode_upload_ticket(ticket)["key"]
    storage.put(key, 1000, "image/png")
    confirm_cover(client, teacher, course_id, ticket)

    assert client.delete(f"{API}/courses/{course_id}", headers=auth(teacher)).status_code == 204
    assert key not in storage.objects
