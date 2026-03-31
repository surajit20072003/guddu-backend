from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from authentication.models import Chapter, Course, Subject, Syllabus, Topic


class PublicContentEndpointsTest(APITestCase):
    def setUp(self):
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
            syllabus=self.syllabus, title="Chapter 1", chapter_number=1, status="PUBLISHED", is_active=True
        )
        self.topic = Topic.objects.create(
            chapter=self.chapter,
            title="Topic 1",
            order=1,
            status="PUBLISHED",
            is_active=True,
            video_url="https://example.com/v.mp4",
            notes="Notes",
            attachments=[{"type": "pdf", "url": "https://example.com/a.pdf"}],
        )

    def test_public_endpoints_read_only(self):
        self.assertEqual(self.client.get("/api/auth/courses/").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.post("/api/auth/courses/", {}, format="json").status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_public_listing_chain(self):
        self.assertEqual(
            self.client.get(f"/api/auth/courses/{self.course.id}/subjects/").status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get(f"/api/auth/subjects/{self.subject.id}/syllabi/").status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get(f"/api/auth/syllabi/{self.syllabus.id}/chapters/").status_code,
            status.HTTP_200_OK,
        )
        topics_resp = self.client.get(f"/api/auth/chapters/{self.chapter.id}/topics/")
        self.assertEqual(topics_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(topics_resp.data[0]["title"], "Topic 1")
        self.assertIn("notes", topics_resp.data[0])
        self.assertIn("attachments", topics_resp.data[0])

    def test_soft_delete_visibility_for_course(self):
        self.course.is_active = False
        self.course.save()

        self.assertEqual(len(self.client.get("/api/auth/courses/").data), 0)
        self.assertEqual(len(self.client.get(f"/api/auth/courses/{self.course.id}/subjects/").data), 0)
        self.assertEqual(len(self.client.get(f"/api/auth/subjects/{self.subject.id}/syllabi/").data), 0)
        self.assertEqual(len(self.client.get(f"/api/auth/syllabi/{self.syllabus.id}/chapters/").data), 0)
        self.assertEqual(len(self.client.get(f"/api/auth/chapters/{self.chapter.id}/topics/").data), 0)

    def test_soft_delete_visibility_for_subject(self):
        self.subject.is_active = False
        self.subject.save()

        self.assertEqual(len(self.client.get(f"/api/auth/subjects/{self.subject.id}/syllabi/").data), 0)
        self.assertEqual(len(self.client.get(f"/api/auth/syllabi/{self.syllabus.id}/chapters/").data), 0)
        self.assertEqual(len(self.client.get(f"/api/auth/chapters/{self.chapter.id}/topics/").data), 0)

    def test_nonexistent_resource_scope_returns_empty(self):
        self.assertEqual(len(self.client.get("/api/auth/courses/99999/subjects/").data), 0)
        self.assertEqual(len(self.client.get("/api/auth/subjects/99999/syllabi/").data), 0)
        self.assertEqual(len(self.client.get("/api/auth/syllabi/99999/chapters/").data), 0)
        self.assertEqual(len(self.client.get("/api/auth/chapters/99999/topics/").data), 0)

