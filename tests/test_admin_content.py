from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from authentication.models import Chapter, Course, Subject, Syllabus, Topic


class AdminContentEndpointsTest(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(email="admin@test.com", password="pass1234")
        self.admin.is_staff = True
        self.admin.save()

        self.user = user_model.objects.create_user(email="user@test.com", password="pass1234")

        self.course = Course.objects.create(
            title="Course A", grade="10", status="PUBLISHED", is_active=True
        )
        self.subject = Subject.objects.create(
            course=self.course, name="Physics", order=1, status="PUBLISHED", is_active=True
        )
        self.syllabus = Syllabus.objects.create(
            subject=self.subject, title="Syllabus", academic_year="2025-26", status="PUBLISHED", is_active=True
        )
        self.chapter = Chapter.objects.create(
            syllabus=self.syllabus, title="Electricity", chapter_number=1, status="PUBLISHED", is_active=True
        )
        self.topic = Topic.objects.create(
            chapter=self.chapter, title="Current", order=1, status="PUBLISHED", is_active=True
        )

    def test_admin_endpoints_require_authentication(self):
        response = self.client.get("/api/auth/admin/courses/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_write_requires_staff(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/auth/admin/courses/",
            {"title": "Nope", "grade": "9", "status": "PUBLISHED", "is_active": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_hierarchy_create_success(self):
        self.client.force_authenticate(self.admin)

        course_resp = self.client.post(
            "/api/auth/admin/courses/",
            {"title": "Course B", "grade": "9", "status": "PUBLISHED", "is_active": True},
            format="json",
        )
        self.assertEqual(course_resp.status_code, status.HTTP_201_CREATED)
        course_id = course_resp.data["id"]

        subject_resp = self.client.post(
            "/api/auth/admin/subjects/",
            {"course": course_id, "name": "Math", "order": 1, "status": "PUBLISHED", "is_active": True},
            format="json",
        )
        self.assertEqual(subject_resp.status_code, status.HTTP_201_CREATED)
        subject_id = subject_resp.data["id"]

        syllabus_resp = self.client.post(
            "/api/auth/admin/syllabi/",
            {
                "subject": subject_id,
                "title": "Syllabus",
                "academic_year": "2026-27",
                "status": "PUBLISHED",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(syllabus_resp.status_code, status.HTTP_201_CREATED)
        syllabus_id = syllabus_resp.data["id"]

        chapter_resp = self.client.post(
            "/api/auth/admin/chapters/",
            {
                "syllabus": syllabus_id,
                "title": "Algebra",
                "chapter_number": 1,
                "status": "PUBLISHED",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(chapter_resp.status_code, status.HTTP_201_CREATED)
        chapter_id = chapter_resp.data["id"]

        topic_resp = self.client.post(
            "/api/auth/admin/topics/",
            {
                "chapter": chapter_id,
                "title": "Linear Equations",
                "order": 1,
                "status": "PUBLISHED",
                "is_active": True,
                "notes": "n",
                "attachments": [],
            },
            format="json",
        )
        self.assertEqual(topic_resp.status_code, status.HTTP_201_CREATED)

