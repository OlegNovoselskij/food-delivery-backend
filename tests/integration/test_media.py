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
