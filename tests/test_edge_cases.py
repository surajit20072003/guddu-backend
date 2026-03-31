from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from authentication.models import Chapter, Course, Subject, Syllabus, Topic


class ContentEdgeCasesTest(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(email="admin2@test.com", password="pass1234")
        self.admin.is_staff = True
        self.admin.save()
        self.client.force_authenticate(self.admin)

        self.course = Course.objects.create(title="Course A", grade="10", status="PUBLISHED", is_active=True)
        self.subject = Subject.objects.create(course=self.course, name="Physics", order=1, status="PUBLISHED", is_active=True)
        self.syllabus = Syllabus.objects.create(subject=self.subject, title="S", academic_year="2025-26", status="PUBLISHED", is_active=True)
        self.chapter = Chapter.objects.create(syllabus=self.syllabus, title="C1", chapter_number=1, status="PUBLISHED", is_active=True)
        self.topic = Topic.objects.create(chapter=self.chapter, title="T1", order=1, status="PUBLISHED", is_active=True)

    def test_invalid_foreign_keys(self):
        resp_subject = self.client.post(
            "/api/auth/admin/subjects/",
            {"course": 999999, "name": "Math", "order": 1, "status": "PUBLISHED", "is_active": True},
            format="json",
        )
        self.assertEqual(resp_subject.status_code, status.HTTP_400_BAD_REQUEST)

        resp_chapter = self.client.post(
            "/api/auth/admin/chapters/",
            {"syllabus": 999999, "title": "Bad", "chapter_number": 1, "status": "PUBLISHED", "is_active": True},
            format="json",
        )
        self.assertEqual(resp_chapter.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_required_fields(self):
        resp_course = self.client.post(
            "/api/auth/admin/courses/",
            {"description": "Missing title/grade"},
            format="json",
        )
        self.assertEqual(resp_course.status_code, status.HTTP_400_BAD_REQUEST)

        resp_topic = self.client.post(
            "/api/auth/admin/topics/",
            {"title": "Missing chapter"},
            format="json",
        )
        self.assertEqual(resp_topic.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_unique_constraints(self):
        dup_subject = self.client.post(
            "/api/auth/admin/subjects/",
            {"course": self.course.id, "name": "Physics", "order": 2, "status": "PUBLISHED", "is_active": True},
            format="json",
        )
        self.assertEqual(dup_subject.status_code, status.HTTP_400_BAD_REQUEST)

        dup_chapter = self.client.post(
            "/api/auth/admin/chapters/",
            {"syllabus": self.syllabus.id, "title": "Duplicate #", "chapter_number": 1, "status": "PUBLISHED", "is_active": True},
            format="json",
        )
        self.assertEqual(dup_chapter.status_code, status.HTTP_400_BAD_REQUEST)

        dup_topic_order = self.client.post(
            "/api/auth/admin/topics/",
            {"chapter": self.chapter.id, "title": "Duplicate order", "order": 1, "status": "PUBLISHED", "is_active": True},
            format="json",
        )
        self.assertEqual(dup_topic_order.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_order_boundary(self):
        resp_negative_order = self.client.post(
            "/api/auth/admin/topics/",
            {"chapter": self.chapter.id, "title": "Neg", "order": -1, "status": "PUBLISHED", "is_active": True},
            format="json",
        )
        self.assertEqual(resp_negative_order.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_query_param_types(self):
        response = self.client.get("/api/auth/admin/subjects/?course_id=not-an-int")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_slug_vs_id_mismatch(self):
        self.assertEqual(
            self.client.get(f"/api/auth/courses/{self.course.id}/full-tree/").status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get("/api/auth/courses/1234567890/full-tree/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.get("/api/auth/courses/wrong-slug/full-tree/").status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_data_volume_stress_basic_scoping(self):
        for i in range(10):
            course = Course.objects.create(title=f"Course {i}", grade="9", status="PUBLISHED", is_active=True)
            sub = Subject.objects.create(course=course, name=f"Subject {i}", order=1, status="PUBLISHED", is_active=True)
            syl = Syllabus.objects.create(subject=sub, title="S", academic_year="2025-26", status="PUBLISHED", is_active=True)
            ch = Chapter.objects.create(syllabus=syl, title="C", chapter_number=1, status="PUBLISHED", is_active=True)
            Topic.objects.create(chapter=ch, title="T", order=1, status="PUBLISHED", is_active=True)

        public_courses = self.client.get("/api/auth/courses/")
        self.assertGreaterEqual(len(public_courses.data), 11)

        scoped_subjects = self.client.get(f"/api/auth/courses/{self.course.id}/subjects/")
        self.assertEqual(len(scoped_subjects.data), 1)

