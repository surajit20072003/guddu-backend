from unittest.mock import patch

from django.test import TestCase

from authentication.cron import process_topic_batch
from authentication.models import Chapter, Course, Subject, Syllabus, Topic, VideoResult


class CronJobsTest(TestCase):
    def setUp(self):
        self.course = Course.objects.create(title="Course A", grade="10", status="PUBLISHED", is_active=True)
        self.subject = Subject.objects.create(course=self.course, name="Physics", order=1, status="PUBLISHED", is_active=True)
        self.syllabus = Syllabus.objects.create(subject=self.subject, title="S", academic_year="2025-26", status="PUBLISHED", is_active=True)
        self.chapter = Chapter.objects.create(syllabus=self.syllabus, title="C1", chapter_number=1, status="PUBLISHED", is_active=True)
        self.topic = Topic.objects.create(chapter=self.chapter, title="T1", order=1, status="PUBLISHED", is_active=True, search_status="PENDING")

    @patch("authentication.cron.get_youtube_videos")
    def test_process_topic_batch_creates_videos_and_updates_status(self, mock_get_videos):
        mock_get_videos.return_value = [
            {
                "video_id": "abc123",
                "title": "Video 1",
                "full_description": "d",
                "url": "https://youtube.com/watch?v=abc123",
                "thumbnail_url": "https://img.youtube.com/vi/abc123/default.jpg",
                "channel_title": "Channel",
                "published_at": None,
                "duration": "PT10M",
                "view_count": 100,
                "like_count": 10,
                "comment_count": 1,
                "tags": "x,y",
                "category_id": "22",
            }
        ]

        result = process_topic_batch()
        self.assertIn("Processed 1 topics, created 1 videos", result)

        self.topic.refresh_from_db()
        self.assertEqual(self.topic.search_status, "COMPLETED")
        self.assertEqual(VideoResult.objects.filter(topic=self.topic).count(), 1)

    @patch("authentication.cron.get_youtube_videos")
    def test_process_topic_batch_no_results_still_completes(self, mock_get_videos):
        mock_get_videos.return_value = []
        result = process_topic_batch()

        self.assertIn("Processed 1 topics, created 0 videos", result)
        self.topic.refresh_from_db()
        self.assertEqual(self.topic.search_status, "COMPLETED")

    @patch("authentication.cron.get_youtube_videos")
    def test_process_topic_batch_marks_failed_on_exception(self, mock_get_videos):
        mock_get_videos.side_effect = Exception("API down")
        process_topic_batch()

        self.topic.refresh_from_db()
        self.assertEqual(self.topic.search_status, "FAILED")

