from tests.helpers import API, add_quiz, auth, build_course, option_ids


def start_learning(client, student, course):
    enrollment = client.post(f"{API}/courses/{course['course_id']}/enroll", headers=auth(student)).json()
    last = None
    for lesson_id in course["lesson_ids"]:
        last = client.post(
            f"{API}/enrollments/{enrollment['id']}/lessons/{lesson_id}/complete", headers=auth(student)
        ).json()
    return enrollment["id"], last


def test_the_full_learning_journey_ends_with_a_certificate(client, teacher, student, category):
    course = build_course(client, teacher, category.id)
    quiz = add_quiz(client, teacher, course["module_id"])
    headers = auth(student)

    enrollment_id, progress = start_learning(client, student, course)
    assert progress["progress"]["percent"] == 66 and progress["enrollment_status"] == "active"

    attempt = client.post(f"{API}/quizzes/{quiz['quiz_id']}/attempts", headers=headers)
    assert attempt.status_code == 201
    body = attempt.json()
    assert all("is_correct" not in option for question in body["questions"] for option in question["options"])

    answers = [
        {"question_id": quiz["single"]["id"], "option_ids": option_ids(quiz["single"], correct=True)},
        {"question_id": quiz["multiple"]["id"], "option_ids": option_ids(quiz["multiple"], correct=True)},
        {"question_id": quiz["open"]["id"], "text": "Because that is how it works."},
    ]
    submitted = client.post(f"{API}/attempts/{body['id']}/submit", headers=headers, json={"answers": answers}).json()
    assert submitted["status"] == "pending_review" and any(item["needs_review"] for item in submitted["review"])

    pending = client.get(f"{API}/reviews/pending", headers=auth(teacher)).json()
    assert [item["attempt_id"] for item in pending] == [body["id"]]
    reviewed = client.post(
        f"{API}/attempts/{body['id']}/review",
        headers=auth(teacher),
        json={"grades": [{"question_id": quiz["open"]["id"], "points": 5, "comment": "Good answer."}]},
    )
    assert reviewed.status_code == 200 and reviewed.json()["score"] == 100 and reviewed.json()["passed"] is True

    assert client.get(f"{API}/enrollments/{enrollment_id}", headers=headers).json()["status"] == "completed"
    certificates = client.get(f"{API}/certificates/mine", headers=headers).json()
    assert len(certificates) == 1
    number = certificates[0]["certificate_number"]
    assert client.get(f"{API}/certificates/verify/{number}").json()["valid"] is True
    pdf = client.get(f"{API}/certificates/{certificates[0]['id']}/pdf", headers=headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

    types = {item["type"] for item in client.get(f"{API}/notifications", headers=headers).json()["items"]}
    assert {"quiz_graded", "course_completed"} <= types


def test_a_failed_quiz_can_be_retried_only_until_the_limit(client, teacher, student, category):
    course = build_course(client, teacher, category.id, lessons=1)
    quiz = add_quiz(client, teacher, course["module_id"], max_attempts=2)
    start_learning(client, student, course)
    headers = auth(student)

    for _ in range(2):
        attempt = client.post(f"{API}/quizzes/{quiz['quiz_id']}/attempts", headers=headers)
        assert attempt.status_code == 201
        wrong = [
            {"question_id": quiz["single"]["id"], "option_ids": option_ids(quiz["single"], correct=False)},
            {"question_id": quiz["multiple"]["id"], "option_ids": option_ids(quiz["multiple"], correct=False)},
        ]
        result = client.post(
            f"{API}/attempts/{attempt.json()['id']}/submit", headers=headers, json={"answers": wrong}
        ).json()
        assert result["status"] == "graded" and result["passed"] is False

    assert client.post(f"{API}/quizzes/{quiz['quiz_id']}/attempts", headers=headers).status_code == 409

    flipped = {
        "text": "Pick the right one",
        "question_type": "single_choice",
        "points": 2,
        "options": [
            {"id": o["id"], "text": o["text"], "is_correct": not o["is_correct"]} for o in quiz["single"]["options"]
        ],
    }
    locked = client.put(f"{API}/questions/{quiz['single']['id']}", headers=auth(teacher), json=flipped)
    assert locked.status_code == 409
