from rest_framework import status
from rest_framework.test import APITestCase

from authentication.models import Chapter, Course, Subject, Syllabus, Topic


class FullTreeEndpointTest(APITestCase):
    def setUp(self):
        self.course = Course.objects.create(
            title="Course A", grade="10", status="PUBLISHED", is_active=True
        )
        self.subject_2 = Subject.objects.create(
            course=self.course, name="Chemistry", order=2, status="PUBLISHED", is_active=True
        )
        self.subject_1 = Subject.objects.create(
            course=self.course, name="Physics", order=1, status="PUBLISHED", is_active=True
        )

        self.syllabus_1 = Syllabus.objects.create(
            subject=self.subject_1, title="S", academic_year="2025-26", status="PUBLISHED", is_active=True
        )
        self.syllabus_2 = Syllabus.objects.create(
            subject=self.subject_1, title="S", academic_year="2024-25", status="PUBLISHED", is_active=True
        )

        self.chapter_2 = Chapter.objects.create(
            syllabus=self.syllabus_1, title="C2", chapter_number=2, status="PUBLISHED", is_active=True
        )
        self.chapter_1 = Chapter.objects.create(
            syllabus=self.syllabus_1, title="C1", chapter_number=1, status="PUBLISHED", is_active=True
        )

        Topic.objects.create(chapter=self.chapter_1, title="T2", order=2, status="PUBLISHED", is_active=True)
        Topic.objects.create(chapter=self.chapter_1, title="T1", order=1, status="PUBLISHED", is_active=True)

    def test_full_tree_by_id_includes_nested_and_ordered(self):
        resp = self.client.get(f"/api/auth/courses/{self.course.id}/full-tree/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        data = resp.data
        self.assertEqual(data["id"], self.course.id)
        self.assertIn("subjects", data)

        subject_orders = [s["order"] for s in data["subjects"]]
        self.assertEqual(subject_orders, sorted(subject_orders))

        syllabi = data["subjects"][0]["syllabi"]
        self.assertEqual(syllabi[0]["academic_year"], "2025-26")

        chapters = syllabi[0]["chapters"]
        chapter_numbers = [c["chapter_number"] for c in chapters]
        self.assertEqual(chapter_numbers, sorted(chapter_numbers))

        topics = chapters[0]["topics"]
        topic_orders = [t["order"] for t in topics]
        self.assertEqual(topic_orders, sorted(topic_orders))

    def test_full_tree_by_slug(self):
        resp = self.client.get(f"/api/auth/courses/{self.course.slug}/full-tree/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["slug"], self.course.slug)

    def test_full_tree_excludes_inactive_nodes(self):
        self.chapter_1.is_active = False
        self.chapter_1.save()

        resp = self.client.get(f"/api/auth/courses/{self.course.id}/full-tree/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        chapters = resp.data["subjects"][0]["syllabi"][0]["chapters"]
        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0]["chapter_number"], 2)

    def test_full_tree_invalid_id_or_slug(self):
        self.assertEqual(
            self.client.get("/api/auth/courses/999999/full-tree/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.get("/api/auth/courses/not-a-real-slug/full-tree/").status_code,
            status.HTTP_404_NOT_FOUND,
        )

