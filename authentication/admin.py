from django.contrib import admin
from .models import Course, Syllabus, Subject, Chapter, Topic

# Register your models here.

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'grade', 'is_active', 'created_at']
    list_filter = ['grade', 'is_active']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Syllabus)
class SyllabusAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'academic_year', 'is_active', 'created_at']
    list_filter = ['is_active', 'academic_year']
    search_fields = ['title', 'description', 'course__title']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'syllabus', 'order', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description', 'syllabus__title']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['order', 'name']


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'chapter_number', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['title', 'description', 'subject__name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['chapter_number']


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['title', 'chapter', 'order', 'search_status', 'last_searched_at', 'is_active']
    list_filter = ['search_status', 'is_active']
    search_fields = ['title', 'description', 'chapter__title']
    readonly_fields = ['search_status', 'last_searched_at', 'created_at', 'updated_at']
    ordering = ['order']
