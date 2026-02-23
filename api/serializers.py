

from rest_framework import serializers
from .models import SearchRequest, KeywordTag

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


class KeywordTagSerializer(serializers.ModelSerializer):
    """Serializer to show a tag"""
    class Meta:
        model = KeywordTag
        fields = ['id', 'tag_text', 'status', 'last_searched_at']