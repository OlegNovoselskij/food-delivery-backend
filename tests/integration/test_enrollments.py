from app.models.email_outbox import EmailOutbox
from tests.helpers import API, auth, build_course, create_user


def enroll(client, user, course_id):
    return client.post(f"{API}/courses/{course_id}/enroll", headers=auth(user))


def pay(client, user, enrollment_id, token="tok_visa"):
    return client.post(
        f"{API}/enrollments/{enrollment_id}/pay",
        headers=auth(user),
        json={"method": "card", "payment_token": token},
    )


def test_a_free_course_activates_the_enrollment_at_once(client, teacher, student, category):
    course_id = build_course(client, teacher, category.id)["course_id"]
    response = enroll(client, student, course_id)
    assert response.status_code == 201 and response.json()["status"] == "active"


def test_a_paid_course_waits_for_the_payment(client, db, teacher, student, category):
    course = build_course(client, teacher, category.id, price="49.00")
    enrollment = enroll(client, student, course["course_id"]).json()
    locked = course["lesson_ids"][1]
    assert enrollment["status"] == "pending_payment"
    assert client.get(f"{API}/lessons/{locked}", headers=auth(student)).status_code == 403

    assert pay(client, student, enrollment["id"], "tok_declined").status_code == 402
    state = client.get(f"{API}/enrollments/{enrollment['id']}", headers=auth(student)).json()["status"]
    assert state == "pending_payment"

    paid = pay(client, student, enrollment["id"])
    assert paid.status_code == 200 and paid.json()["status"] == "active"
    assert paid.json()["payment"]["status"] == "succeeded"
    assert client.get(f"{API}/lessons/{locked}", headers=auth(student)).status_code == 200

    assert pay(client, student, enrollment["id"]).status_code == 409
    assert enroll(client, student, course["course_id"]).status_code == 409
    assert db.query(EmailOutbox).filter(EmailOutbox.subject.like("Payment received%")).count() == 1
    types = {item["type"] for item in client.get(f"{API}/notifications", headers=auth(student)).json()["items"]}
    assert "payment_succeeded" in types


def test_cancelling_refunds_the_payment_and_closes_access(client, teacher, student, category):
    course = build_course(client, teacher, category.id, price="49.00")
    enrollment = enroll(client, student, course["course_id"]).json()
    pay(client, student, enrollment["id"])

    cancelled = client.post(f"{API}/enrollments/{enrollment['id']}/cancel", headers=auth(student))
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled" and cancelled.json()["payment"]["status"] == "refunded"
    assert client.get(f"{API}/lessons/{course['lesson_ids'][1]}", headers=auth(student)).status_code == 403

    again = enroll(client, student, course["course_id"]).json()
    assert again["id"] == enrollment["id"] and again["status"] == "pending_payment"


def test_teachers_cannot_enroll_in_their_own_courses(client, teacher, category):
    course_id = build_course(client, teacher, category.id)["course_id"]
    assert enroll(client, teacher, course_id).status_code == 409


def test_enrollments_of_other_students_are_hidden(client, db, teacher, student, category):
    course_id = build_course(client, teacher, category.id)["course_id"]
    enrollment_id = enroll(client, student, course_id).json()["id"]
    other = create_user(db, "student", email="other@example.com")
    assert client.get(f"{API}/enrollments/{enrollment_id}", headers=auth(other)).status_code == 404
