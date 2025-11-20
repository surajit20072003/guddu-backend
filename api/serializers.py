

from rest_framework import serializers
from .models import SearchRequest, KeywordTag, VideoResult

class SearchUploadSerializer(serializers.ModelSerializer):
    """
    Serializer for validating the file upload from the admin.
    """
    tags_from_user = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    class_level = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    year = serializers.IntegerField(
        required=False, 
        allow_null=True
    )

    class Meta:
        model = SearchRequest
        fields = ['uploaded_file', 'tags_from_user', 'class_level','year']


class VideoResultSerializer(serializers.ModelSerializer):
    """Serializer for returning video results."""
    class Meta:
        model = VideoResult
        fields = [
            'title', 'video_id', 'url', 'thumbnail_url',
            'channel_title', 'published_at', 'duration',
            'view_count', 'like_count', 'comment_count',
            'tags_from_video', 'description'
        ]

class KeywordTagSerializer(serializers.ModelSerializer):
    """Serializer to show a tag and its related videos."""
    videos = VideoResultSerializer(many=True, read_only=True)

    class Meta:
        model = KeywordTag
        fields = ['tag_text', 'status', 'last_searched_at', 'videos']