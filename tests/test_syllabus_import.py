from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from authentication.models import Course, Subject, Syllabus


class SyllabusImportEndpointTest(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(email="import-admin@test.com", password="pass1234")
        self.admin.is_staff = True
        self.admin.save()

        self.course = Course.objects.create(title="Course A", grade="10", status="PUBLISHED", is_active=True)
        self.subject = Subject.objects.create(
            course=self.course, name="Physics", order=1, status="PUBLISHED", is_active=True
        )

    def _auth_admin(self):
        self.client.force_authenticate(self.admin)

    @patch("authentication.views.parse_syllabus_text")
    @patch("authentication.views.extract_text_from_uploaded_file")
    def test_import_syllabus_success(self, mock_extract, mock_parse):
        self._auth_admin()
        mock_extract.return_value = "mocked text"
        mock_parse.return_value = [
            {"chapter_number": 1, "title": "Chapter 1", "topics": ["Topic 1", "Topic 2"]},
            {"chapter_number": 2, "title": "Chapter 2", "topics": ["Topic 3"]},
        ]

        upload = SimpleUploadedFile("syllabus.pdf", b"pdf-bytes", content_type="application/pdf")
        response = self.client.post(
            "/api/auth/admin/syllabi/import/",
            {
                "file": upload,
                "subject_id": self.subject.id,
                "title": "Imported Syllabus",
                "academic_year": "2026-27",
                "status": "PUBLISHED",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("syllabus_id", response.data)
        self.assertEqual(response.data["chapters_created"], 2)
        self.assertEqual(response.data["topics_created"], 3)

    def test_import_requires_subject_and_file(self):
        self._auth_admin()

        no_file = self.client.post("/api/auth/admin/syllabi/import/", {"subject_id": self.subject.id})
        self.assertEqual(no_file.status_code, status.HTTP_400_BAD_REQUEST)

        upload = SimpleUploadedFile("syllabus.pdf", b"pdf-bytes", content_type="application/pdf")
        no_subject = self.client.post("/api/auth/admin/syllabi/import/", {"file": upload})
        self.assertEqual(no_subject.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("authentication.views.extract_text_from_uploaded_file")
    def test_import_parse_failure_does_not_create_syllabus(self, mock_extract):
        self._auth_admin()
        mock_extract.side_effect = ValueError("Could not extract readable text from the file")

        before_count = Syllabus.objects.count()
        upload = SimpleUploadedFile("broken.pdf", b"bad", content_type="application/pdf")
        response = self.client.post(
            "/api/auth/admin/syllabi/import/",
            {"file": upload, "subject_id": self.subject.id, "title": "Will Fail"},
        )
        after_count = Syllabus.objects.count()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(before_count, after_count)

