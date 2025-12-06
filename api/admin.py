from django.contrib import admin
from .models import SearchRequest, KeywordTag, VideoResult
import re

# -----------------------------------------------------------------
# This is the Class filter (no change)
# -----------------------------------------------------------------
class ClassLevelFilter(admin.SimpleListFilter):
    title = 'Class Level' # Title of the filter
    parameter_name = 'class_level' # The URL parameter

    def lookups(self, request, model_admin):
        """
        Finds all unique class levels from the SearchRequests
        and creates the filter options.
        """
        # Get all non-empty, unique class levels
        levels = SearchRequest.objects.exclude(class_level__isnull=True).exclude(class_level__exact='')
        levels = levels.values_list('class_level', flat=True).distinct().order_by('class_level')
        
        # Return a list of tuples (value, display_name)
        return [(level, level) for level in levels]

    def queryset(self, request, queryset):
        """
        Filters the list based on the user's click.
        """
        if self.value():
            # If user clicked "1", find all tags linked
            # to a SearchRequest with class_level="1"
            return queryset.filter(search_requests__class_level=self.value())
        return queryset

# -----------------------------------------------------------------
# --- ADD THIS NEW YEAR FILTER ---
# -----------------------------------------------------------------
class YearFilter(admin.SimpleListFilter):
    title = 'Year' # Title of the filter
    parameter_name = 'year' # The URL parameter

    def lookups(self, request, model_admin):
        """
        Finds all unique years from the SearchRequests
        and creates the filter options.
        """
        # Get all non-empty, unique years
        years = SearchRequest.objects.exclude(year__isnull=True)
        # Order by year descending (e.g., 2025, 2024, 2023)
        years = years.values_list('year', flat=True).distinct().order_by('-year')
        
        # Return a list of tuples (value, display_name)
        return [(year, year) for year in years]

    def queryset(self, request, queryset):
        """
        Filters the list based on the user's click.
        """
        if self.value():
            # If user clicked "2025", find all tags linked
            # to a SearchRequest with year=2025
            return queryset.filter(search_requests__year=self.value())
        return queryset

# -----------------------------------------------------------------
# This is the inline view (no change)
# -----------------------------------------------------------------
class VideoResultInline(admin.TabularInline):
    model = VideoResult
    fields = ['approval_status', 'title', 'video_id', 'view_count', 'like_count', 'url'] 
    readonly_fields = ['title', 'video_id', 'view_count', 'like_count', 'url']
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return True 

# -----------------------------------------------------------------
# This is the updated KeywordTag admin
# -----------------------------------------------------------------
@admin.register(KeywordTag)
class KeywordTagAdmin(admin.ModelAdmin):
    
    list_display = ['tag_text', 'status', 'last_searched_at']
    
    # --- ADD THE YearFilter TO THE LIST ---
    list_filter = [ClassLevelFilter, YearFilter, 'status'] 
    
    search_fields = ['tag_text']
    inlines = [VideoResultInline]

# -----------------------------------------------------------------
# This is the updated SearchRequest admin
# -----------------------------------------------------------------
@admin.register(SearchRequest)
class SearchRequestAdmin(admin.ModelAdmin):
    
    # --- ADD 'year' TO THE DISPLAY AND FILTERS ---
    list_display = ['id', 'status', 'class_level', 'year', 'created_at']
    list_filter = ['status', 'class_level', 'year']

# -----------------------------------------------------------------
# VideoResult standalone admin (for easy video management)
# -----------------------------------------------------------------
@admin.register(VideoResult)
class VideoResultAdmin(admin.ModelAdmin):
    list_display = ['video_title', 'approval_status', 'get_topic_info', 'get_tag_info', 
                    'view_count', 'like_count', 'channel_title']
    list_filter = ['approval_status', 'topic__chapter__subject__syllabus__course__grade', 'tag']
    search_fields = ['title', 'video_id', 'channel_title', 'description']
    list_editable = ['approval_status']  # Allow quick editing from list view
    
    readonly_fields = ['video_id', 'title', 'description', 'url', 'thumbnail_url', 
                       'channel_title', 'published_at', 'duration', 'view_count', 
                       'like_count', 'comment_count', 'tags_from_video', 'category_id',
                       'get_full_hierarchy']
    
    # Organize fields in detail view
    fieldsets = (
        ('Approval', {
            'fields': ('approval_status',)
        }),
        ('Linked To', {
            'fields': ('tag', 'topic', 'get_full_hierarchy')
        }),
        ('Video Details', {
            'fields': ('video_id', 'title', 'description', 'url', 'thumbnail_url')
        }),
        ('Channel Info', {
            'fields': ('channel_title', 'published_at')
        }),
        ('Statistics', {
            'fields': ('view_count', 'like_count', 'comment_count', 'duration')
        }),
        ('Metadata', {
            'fields': ('tags_from_video', 'category_id'),
            'classes': ('collapse',)
        }),
    )
    
    def video_title(self, obj):
        """Truncate long titles"""
        return obj.title[:60] + '...' if len(obj.title) > 60 else obj.title
    video_title.short_description = 'Title'
    
    def get_topic_info(self, obj):
        """Show topic with chapter and subject"""
        if obj.topic:
            return f"{obj.topic.title} (Ch: {obj.topic.chapter.title})"
        return "-"
    get_topic_info.short_description = 'Topic'
    
    def get_tag_info(self, obj):
        """Show tag if exists"""
        if obj.tag:
            return obj.tag.tag_text
        return "-"
    get_tag_info.short_description = 'Tag'
    
    def get_full_hierarchy(self, obj):
        """Show complete hierarchy for topic-based videos"""
        if obj.topic:
            topic = obj.topic
            chapter = topic.chapter
            subject = chapter.subject
            syllabus = subject.syllabus
            course = syllabus.course
            
            hierarchy = f"""
            Course: {course.title} ({course.grade})
            Syllabus: {syllabus.title} ({syllabus.academic_year})
            Subject: {subject.name}
            Chapter: {chapter.title} (Ch. {chapter.chapter_number})
            Topic: {topic.title}
            """
            return hierarchy.strip()
        elif obj.tag:
            return f"Tag: {obj.tag.tag_text}"
        return "No hierarchy"
    get_full_hierarchy.short_description = 'Full Hierarchy'
    
    def has_add_permission(self, request):
        # Don't allow manual video creation
        return False