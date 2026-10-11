from decimal import Decimal

from tests.helpers import API, auth, build_course, create_user


def test_reviews_need_progress_and_keep_the_rating_in_sync(client, teacher, student, category):
    course = build_course(client, teacher, category.id)
    course_id, headers, review = course["course_id"], auth(student), {"rating": 5, "comment": "Great"}
    assert client.post(f"{API}/courses/{course_id}/reviews", headers=headers, json=review).status_code == 403

    enrollment_id = client.post(f"{API}/courses/{course_id}/enroll", headers=headers).json()["id"]
    assert client.post(f"{API}/courses/{course_id}/reviews", headers=headers, json=review).status_code == 403

    client.post(f"{API}/enrollments/{enrollment_id}/lessons/{course['lesson_ids'][0]}/complete", headers=headers)
    created = client.post(f"{API}/courses/{course_id}/reviews", headers=headers, json=review)
    assert created.status_code == 201
    assert client.post(f"{API}/courses/{course_id}/reviews", headers=headers, json=review).status_code == 409

    shown = client.get(f"{API}/courses/{course_id}").json()
    assert shown["rating_avg"] == 5.0 and shown["reviews_count"] == 1
    assert client.delete(f"{API}/reviews/{created.json()['id']}", headers=headers).status_code == 204
    assert client.get(f"{API}/courses/{course_id}").json()["rating_avg"] is None


def test_reports_are_admin_only_and_csv_is_escaped(client, teacher, admin, category):
    build_course(client, teacher, category.id, title="=1+1")
    assert client.get(f"{API}/reports/admin/overview", headers=auth(teacher)).status_code == 403
    overview = client.get(f"{API}/reports/admin/overview", headers=auth(admin))
    assert overview.status_code == 200 and overview.json()["courses"]["published"] == 1

    csv_response = client.get(f"{API}/reports/admin/courses", params={"format": "csv"}, headers=auth(admin))
    assert csv_response.headers["content-type"].startswith("text/csv") and "'=1+1" in csv_response.text


def test_revenue_counts_successful_payments(client, teacher, student, admin, category):
    course_id = build_course(client, teacher, category.id, price="50.00")["course_id"]
    enrollment_id = client.post(f"{API}/courses/{course_id}/enroll", headers=auth(student)).json()["id"]
    client.post(
        f"{API}/enrollments/{enrollment_id}/pay",
        headers=auth(student),
        json={"method": "card", "payment_token": "tok_visa"},
    )
    breakdown = client.get(
        f"{API}/reports/admin/revenue/breakdown", params={"by": "course"}, headers=auth(admin)
    ).json()
    assert Decimal(str(breakdown["total_revenue"])) == Decimal("50")


def test_teachers_only_see_reports_of_their_own_courses(client, db, teacher, category):
    course_id = build_course(client, teacher, category.id)["course_id"]
    other = create_user(db, "teacher", email="other@example.com")
    url = f"{API}/reports/teacher/courses/{course_id}/funnel"
    assert client.get(url, headers=auth(other)).status_code == 404
    assert client.get(url, headers=auth(teacher)).status_code == 200


def test_recommendations_skip_courses_the_student_already_has(client, teacher, student, category):
    first = build_course(client, teacher, category.id, title="First course")["course_id"]
    second = build_course(client, teacher, category.id, title="Second course")["course_id"]
    client.post(f"{API}/courses/{first}/enroll", headers=auth(student))
    result = client.get(f"{API}/recommendations", headers=auth(student)).json()
    assert [item["course"]["id"] for item in result] == [second]
