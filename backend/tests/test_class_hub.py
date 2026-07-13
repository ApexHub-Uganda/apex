"""Tests for class hub overview, detail, and prefect management."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Class, ClassPrefect, Stream
from apps.core.constants import UserRole
from apps.staff.services import onboard_staff
from apps.students.models import Student
from apps.subscriptions.services import assign_plan_features


@pytest.fixture
def academic_setup(db, tenant):
    year = AcademicYear.objects.create(
        tenant=tenant, name="2026", start_date="2026-01-01", end_date="2026-12-31", is_current=True,
    )
    school_class = Class.objects.create(
        tenant=tenant, name="Grade 7", code="G7A", academic_year=year, capacity=40,
    )
    stream = Stream.objects.create(tenant=tenant, school_class=school_class, name="East")
    return year, school_class, stream


@pytest.fixture
def class_hub_plan(plan):
    assign_plan_features(plan, [
        "classes", "streams", "student_management", "staff_management",
        "academic_years", "terms", "class_teacher_tools", "parent_management",
    ])
    return plan


@pytest.fixture
def class_teacher_user(db, tenant, academic_setup, monkeypatch):
    class _EmailResult:
        success = True
        message = ""

    monkeypatch.setattr(
        "apps.staff.portal_credentials.EmailService.send",
        lambda *args, **kwargs: _EmailResult(),
    )
    _, school_class, _ = academic_setup
    staff = onboard_staff(
        tenant,
        data={
            "first_name": "Class",
            "last_name": "Teacher",
            "email": "classteacher@test.edu",
            "phone": "0700000001",
            "portal_role": UserRole.CLASS_TEACHER,
            "date_joined": "2026-01-01",
        },
    )
    teacher = staff.teacher_profile
    school_class.class_teacher = teacher
    school_class.save(update_fields=["class_teacher"])
    return staff.user, teacher, school_class


@pytest.mark.django_db
def test_classes_overview_lists_streams_nested(school_admin, class_hub_plan, academic_setup):
    _, school_class, stream = academic_setup
    client = APIClient()
    client.force_authenticate(user=school_admin)
    response = client.get("/api/v1/academics/classes/overview/")
    assert response.status_code == 200
    rows = response.json()["data"]
    assert len(rows) >= 1
    row = next(item for item in rows if item["id"] == str(school_class.id))
    assert row["has_streams"] is True
    assert len(row["streams"]) == 1
    assert row["streams"][0]["name"] == stream.name


@pytest.mark.django_db
def test_class_hub_detail_includes_teacher_students_and_null_prefects(
    school_admin, class_hub_plan, academic_setup,
):
    _, school_class, stream = academic_setup
    Student.objects.create(
        tenant=school_admin.tenant,
        admission_number="HUB001",
        first_name="Hub",
        last_name="Student",
        date_of_birth="2012-01-01",
        gender="male",
        enrollment_date="2026-01-15",
        school_class=school_class,
        stream=stream,
        created_by=school_admin,
        updated_by=school_admin,
    )
    client = APIClient()
    client.force_authenticate(user=school_admin)
    response = client.get(f"/api/v1/academics/classes/{school_class.id}/hub/?stream={stream.id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["class_teacher"]["display"] == "Not assigned"
    assert data["student_count"] == 1
    assert data["prefects"] == []
    assert data["can_manage_prefects"] is True


@pytest.mark.django_db
def test_class_teacher_can_appoint_prefect(class_teacher_user, class_hub_plan, academic_setup):
    user, _, school_class = class_teacher_user
    _, _, stream = academic_setup
    student = Student.objects.create(
        tenant=user.tenant,
        admission_number="PF001",
        first_name="Prefect",
        last_name="Candidate",
        date_of_birth="2012-02-02",
        gender="female",
        enrollment_date="2026-01-15",
        school_class=school_class,
        stream=stream,
        created_by=user,
        updated_by=user,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f"/api/v1/academics/classes/{school_class.id}/prefects/",
        {"student": str(student.id), "role": "head", "stream": str(stream.id)},
        format="json",
    )
    assert response.status_code == 201
    assert ClassPrefect.objects.filter(student=student, school_class=school_class).exists()


@pytest.mark.django_db
def test_streams_write_requires_classes_feature_only(school_admin, class_hub_plan, academic_setup):
    _, school_class, _ = academic_setup
    client = APIClient()
    client.force_authenticate(user=school_admin)
    response = client.post(
        "/api/v1/academics/streams/",
        {"name": "North", "school_class": str(school_class.id), "capacity": 35},
        format="json",
    )
    assert response.status_code in (200, 201)


@pytest.mark.django_db
def test_multiple_prefects_can_be_appointed(school_admin, class_hub_plan, academic_setup):
    _, school_class, stream = academic_setup
    students = []
    for idx, role in enumerate(["head", "deputy", "prefect"], start=1):
        students.append(Student.objects.create(
            tenant=school_admin.tenant,
            admission_number=f"MP00{idx}",
            first_name=f"Prefect{idx}",
            last_name="Student",
            date_of_birth="2012-01-01",
            gender="male",
            enrollment_date="2026-01-15",
            school_class=school_class,
            stream=stream,
            created_by=school_admin,
            updated_by=school_admin,
        ))

    client = APIClient()
    client.force_authenticate(user=school_admin)
    for student, role in zip(students, ["head", "deputy", "prefect"], strict=True):
        response = client.post(
            f"/api/v1/academics/classes/{school_class.id}/prefects/",
            {"student": str(student.id), "role": role, "stream": str(stream.id)},
            format="json",
        )
        assert response.status_code == 201

    hub = client.get(f"/api/v1/academics/classes/{school_class.id}/hub/?stream={stream.id}")
    assert len(hub.json()["data"]["prefects"]) == 3


@pytest.mark.django_db
def test_class_delete_blocked_when_students_enrolled(school_admin, class_hub_plan, academic_setup):
    _, school_class, stream = academic_setup
    Student.objects.create(
        tenant=school_admin.tenant,
        admission_number="DEL001",
        first_name="Enrolled",
        last_name="Student",
        date_of_birth="2012-01-01",
        gender="male",
        enrollment_date="2026-01-15",
        school_class=school_class,
        stream=stream,
        created_by=school_admin,
        updated_by=school_admin,
    )
    client = APIClient()
    client.force_authenticate(user=school_admin)

    preview = client.get(f"/api/v1/academics/classes/{school_class.id}/deletion-preview/")
    assert preview.json()["data"]["can_delete"] is False

    response = client.delete(f"/api/v1/academics/classes/{school_class.id}/")
    assert response.status_code == 400


@pytest.mark.django_db
def test_class_delete_when_empty(school_admin, class_hub_plan, academic_setup):
    _, school_class, _ = academic_setup
    client = APIClient()
    client.force_authenticate(user=school_admin)

    response = client.delete(f"/api/v1/academics/classes/{school_class.id}/")
    assert response.status_code == 200
    school_class.refresh_from_db()
    assert school_class.is_deleted is True


@pytest.mark.django_db
def test_class_hub_exposes_enroll_permission_for_class_teacher(
    school_admin, class_teacher_user, class_hub_plan, academic_setup,
):
    _, school_class, _ = academic_setup
    admin_client = APIClient()
    admin_client.force_authenticate(user=school_admin)
    admin_response = admin_client.get(f"/api/v1/academics/classes/{school_class.id}/hub/")
    assert admin_response.json()["data"]["permissions"]["can_enroll_students"] is True

    teacher_client = APIClient()
    teacher_client.force_authenticate(user=class_teacher_user[0])
    teacher_response = teacher_client.get(f"/api/v1/academics/classes/{school_class.id}/hub/")
    assert teacher_response.json()["data"]["permissions"]["can_enroll_students"] is True
    assert teacher_response.json()["data"]["permissions"]["can_manage_prefects"] is True


@pytest.mark.django_db
def test_class_teacher_can_create_student_in_assigned_class(
    class_teacher_user, class_hub_plan, academic_setup,
):
    user, _, school_class = class_teacher_user
    _, _, stream = academic_setup
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        "/api/v1/students/",
        {
            "first_name": "Enrolled",
            "last_name": "Student",
            "gender": "male",
            "date_of_birth": "2012-01-01",
            "enrollment_date": "2026-01-15",
            "school_class": str(school_class.id),
            "stream": str(stream.id),
        },
        format="json",
    )
    assert response.status_code in (200, 201), response.content


@pytest.mark.django_db
def test_school_admin_can_create_student_in_class(school_admin, class_hub_plan, academic_setup):
    _, school_class, stream = academic_setup
    client = APIClient()
    client.force_authenticate(user=school_admin)
    response = client.post(
        "/api/v1/students/",
        {
            "first_name": "Enrolled",
            "last_name": "Learner",
            "gender": "female",
            "date_of_birth": "2012-03-03",
            "enrollment_date": "2026-01-15",
            "school_class": str(school_class.id),
            "stream": str(stream.id),
        },
        format="json",
    )
    assert response.status_code in (200, 201), response.content
    payload = response.json()
    body = payload.get("data", payload)
    assert body["admission_number"]


@pytest.mark.django_db
def test_class_hub_exposes_write_permissions_for_school_admin(
    school_admin, class_hub_plan, academic_setup,
):
    _, school_class, _ = academic_setup
    client = APIClient()
    client.force_authenticate(user=school_admin)
    response = client.get(f"/api/v1/academics/classes/{school_class.id}/hub/")
    permissions = response.json()["data"]["permissions"]
    assert permissions["can_write_class"] is True
    assert permissions["can_enroll_students"] is True
    assert permissions["can_manage_streams"] is True


@pytest.mark.django_db
def test_school_admin_can_update_class(school_admin, class_hub_plan, academic_setup):
    _, school_class, _ = academic_setup
    client = APIClient()
    client.force_authenticate(user=school_admin)
    response = client.patch(
        f"/api/v1/academics/classes/{school_class.id}/",
        {"name": "Grade 7 Updated", "room": "Block B"},
        format="json",
    )
    assert response.status_code == 200, response.content
    school_class.refresh_from_db()
    assert school_class.name == "Grade 7 Updated"
    assert school_class.room == "Block B"


@pytest.mark.django_db
def test_module_menu_hides_streams_child(tenant, class_hub_plan):
    from apps.subscriptions.services import assign_plan_features, get_tenant_module_menu

    assign_plan_features(tenant.active_subscription.plan, ["classes", "streams", "academic_years"])
    menu = get_tenant_module_menu(tenant)
    academics = next(item for item in menu if item["key"] == "academics")
    child_keys = {child["feature_key"] for child in academics["children"]}
    assert "streams" not in child_keys
    assert "classes" in child_keys