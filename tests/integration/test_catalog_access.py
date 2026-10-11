from tests.helpers import API, add_quiz, auth, build_course, create_user


def test_only_teachers_create_courses(client, student, category):
    response = client.post(
        f"{API}/courses",
        headers=auth(student),
        json={"category_id": category.id, "title": "Sample course", "level": "beginner", "price": "0"},
    )
    assert response.status_code == 403


def test_drafts_are_visible_only_to_their_owner(client, db, teacher, category):
    course_id = build_course(client, teacher, category.id, publish=False)["course_id"]
    other = create_user(db, "teacher", email="other@example.com")
    assert client.get(f"{API}/courses/{course_id}").status_code == 404
    assert client.get(f"{API}/courses/{course_id}", headers=auth(other)).status_code == 404
    assert client.get(f"{API}/courses/{course_id}", headers=auth(teacher)).status_code == 200


def test_a_course_without_lessons_cannot_be_published(client, teacher, category):
    headers = auth(teacher)
    course = client.post(
        f"{API}/courses",
        headers=headers,
        json={"category_id": category.id, "title": "Empty course", "level": "beginner", "price": "0"},
    ).json()
    assert client.post(f"{API}/courses/{course['id']}/publish", headers=headers).status_code == 409


def test_the_catalog_lists_only_published_courses_and_filters_them(client, teacher, category):
    build_course(client, teacher, category.id, title="Python basics")
    build_course(client, teacher, category.id, title="Design intro")
    build_course(client, teacher, category.id, title="Hidden draft", publish=False)
    assert client.get(f"{API}/courses").json()["total"] == 2
    assert client.get(f"{API}/courses", params={"q": "python"}).json()["total"] == 1


def test_course_cards_report_the_number_of_modules(client, teacher, category):
    course = build_course(client, teacher, category.id)
    extra = client.post(
        f"{API}/courses/{course['course_id']}/modules", headers=auth(teacher), json={"title": "Module 2"}
    )
    assert extra.status_code == 201
    item = client.get(f"{API}/courses").json()["items"][0]
    assert item["modules_count"] == 2
    assert client.get(f"{API}/courses/{course['course_id']}").json()["modules_count"] == 2


def test_a_teacher_cannot_edit_someone_elses_course(client, db, teacher, category):
    course_id = build_course(client, teacher, category.id)["course_id"]
    other = create_user(db, "teacher", email="other@example.com")
    response = client.patch(f"{API}/courses/{course_id}", headers=auth(other), json={"title": "Hijacked title"})
    assert response.status_code == 403


def test_lessons_are_locked_for_people_without_access(client, teacher, student, category):
    course = build_course(client, teacher, category.id)
    preview, locked = course["lesson_ids"]
    assert client.get(f"{API}/lessons/{preview}").status_code == 200
    assert client.get(f"{API}/lessons/{locked}").status_code == 403
    assert client.get(f"{API}/lessons/{locked}", headers=auth(student)).status_code == 403

    assert client.post(f"{API}/courses/{course['course_id']}/enroll", headers=auth(student)).status_code == 201
    assert client.get(f"{API}/lessons/{locked}", headers=auth(student)).status_code == 200
    assert client.get(f"{API}/lessons/{locked}", headers=auth(teacher)).status_code == 200


def test_categories_are_managed_by_admins(client, student, admin):
    assert client.post(f"{API}/categories", headers=auth(student), json={"name": "Math"}).status_code == 403
    assert client.post(f"{API}/categories", headers=auth(admin), json={"name": "Math"}).status_code == 201
    assert client.post(f"{API}/categories", headers=auth(admin), json={"name": " math "}).status_code == 409


def test_the_catalog_is_cached_and_invalidated_on_change(client, teacher, category):
    course_id = build_course(client, teacher, category.id)["course_id"]
    assert client.get(f"{API}/courses").headers["X-Cache"] == "MISS"
    assert client.get(f"{API}/courses").headers["X-Cache"] == "HIT"
    client.patch(f"{API}/courses/{course_id}", headers=auth(teacher), json={"title": "New title"})
    after = client.get(f"{API}/courses")
    assert after.headers["X-Cache"] == "MISS" and after.json()["items"][0]["title"] == "New title"


def test_the_program_reports_the_quiz_of_a_module(client, teacher, category):
    course = build_course(client, teacher, category.id)
    before = client.get(f"{API}/courses/{course['course_id']}/program").json()["modules"][0]
    assert before["has_quiz"] is False and before["quiz_id"] is None and before["quiz_questions_count"] == 0

    quiz = add_quiz(client, teacher, course["module_id"])
    after = client.get(f"{API}/courses/{course['course_id']}/program").json()["modules"][0]
    assert after["has_quiz"] is True
    assert after["quiz_id"] == quiz["quiz_id"]
    assert after["quiz_questions_count"] == 3
