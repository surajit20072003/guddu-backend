
from django.db import models
from django.utils import timezone # We will need this

class SearchRequest(models.Model):
    """
    To track the file upload and class level only.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'), # Means tags have not been extracted yet
        ('COMPLETED', 'Completed'), # Means tags have been extracted
    ]
    uploaded_file = models.FileField(upload_to='uploads/', null=True, blank=True)
    tags_from_user = models.TextField(null=True, blank=True, help_text="Comma-separated tags from user")
    class_level = models.CharField(max_length=100, null=True, blank=True, help_text="e.g., LKG, UKG, Class 1")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Request {self.id} - {self.status}"


class KeywordTag(models.Model):
    """
    This is our "To-Do" list. Each tag is saved only once.
    """
    tag_text = models.CharField(max_length=255, unique=True) # <-- unique=True handles "search only once"
    search_requests = models.ManyToManyField(
        SearchRequest,
        related_name="keywords",
        blank=True
    )
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),     # Means: waiting to be searched
        ('PROCESSING', 'Processing'), # Means: currently being searched
        ('COMPLETED', 'Completed'),   # Means: search is done
        ('FAILED', 'Failed'),       # Means: search failed
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    last_searched_at = models.DateTimeField(null=True, blank=True) # When was it last searched

    def __str__(self):
        return self.tag_text


class VideoResult(models.Model):
    """
    Each video is now linked to a 'KeywordTag'.
    """
    tag = models.ForeignKey(KeywordTag, related_name='videos', on_delete=models.CASCADE)
    APPROVAL_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('DISAPPROVED', 'Disapproved'),
    ]
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_CHOICES,
        default='PENDING'
    )
    
    video_id = models.CharField(max_length=50) # unique=True has been removed
    title = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)
    url = models.URLField(max_length=500)
    thumbnail_url = models.URLField(max_length=500, null=True, blank=True)
    channel_title = models.CharField(max_length=200, null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    duration = models.CharField(max_length=20, null=True, blank=True)
    view_count = models.BigIntegerField(null=True, blank=True)
    like_count = models.BigIntegerField(null=True, blank=True)
    comment_count = models.BigIntegerField(null=True, blank=True)
    tags_from_video = models.TextField(null=True, blank=True) 
    category_id = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return self.title