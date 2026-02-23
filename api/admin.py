from django.contrib import admin
from .models import SearchRequest, KeywordTag
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
# This is the updated KeywordTag admin
# -----------------------------------------------------------------
@admin.register(KeywordTag)
class KeywordTagAdmin(admin.ModelAdmin):
    
    list_display = ['tag_text', 'status', 'last_searched_at']
    
    # --- ADD THE YearFilter TO THE LIST ---
    list_filter = [ClassLevelFilter, YearFilter, 'status'] 
    
    search_fields = ['tag_text']

# -----------------------------------------------------------------
# This is the updated SearchRequest admin
# -----------------------------------------------------------------
@admin.register(SearchRequest)
class SearchRequestAdmin(admin.ModelAdmin):
    
    # --- ADD 'year' TO THE DISPLAY AND FILTERS ---
    list_display = ['id', 'status', 'class_level', 'year', 'created_at']
    list_filter = ['status', 'class_level', 'year']