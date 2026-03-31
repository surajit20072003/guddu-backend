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
    list_display = ['title', 'subject', 'academic_year', 'status', 'is_active', 'created_at']
    list_filter = ['status', 'is_active', 'academic_year']
    search_fields = ['title', 'description', 'subject__name', 'subject__course__title']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'course', 'order', 'status', 'is_active', 'created_at']
    list_filter = ['status', 'is_active']
    search_fields = ['name', 'description', 'course__title']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['order', 'name']


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ['title', 'syllabus', 'chapter_number', 'status', 'is_active', 'created_at']
    list_filter = ['status', 'is_active']
    search_fields = ['title', 'description', 'syllabus__title', 'syllabus__subject__name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['chapter_number']


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['title', 'chapter', 'order', 'search_status', 'last_searched_at', 'status', 'is_active']
    list_filter = ['search_status', 'status', 'is_active']
    search_fields = ['title', 'description', 'chapter__title', 'chapter__syllabus__title']
    readonly_fields = ['search_status', 'last_searched_at', 'created_at', 'updated_at']
    ordering = ['order']
