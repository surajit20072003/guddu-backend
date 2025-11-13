# api/admin.py
from django.contrib import admin
from .models import SearchRequest, KeywordTag, VideoResult
import re

# -----------------------------------------------------------------
# This is the new custom filter
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
    
    # We add the new custom filter
    list_filter = [ClassLevelFilter, 'status'] # <-- THIS IS THE FIX
    
    search_fields = ['tag_text']
    inlines = [VideoResultInline]

# -----------------------------------------------------------------
# This is the SearchRequest admin (no change)
# -----------------------------------------------------------------
@admin.register(SearchRequest)
class SearchRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'class_level', 'created_at']
    list_filter = ['status']