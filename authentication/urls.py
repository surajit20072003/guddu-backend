# authentication/urls.py

from django.urls import path
from .views import *
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Route for user registration
    path('register/', RegisterView.as_view(), name='auth_register'),
    
    # Route for user login, returns access and refresh tokens
    path('login/', LoginView.as_view(), name='auth_login'),
    
    # Route to get a new access token using a refresh token
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Route for user logout (blacklists the refresh token)
    path('logout/', LogoutView.as_view(), name='auth_logout'),
    path('profile/', ProfileView.as_view(), name='user-profile'),
    
    # Plan endpoints
    path('plans/', PlanListView.as_view(), name='plan-list'),
    path('plans/<int:pk>/', PlanDetailView.as_view(), name='plan-detail'),
    
    # Subscription endpoints
    path('subscription/', SubscriptionView.as_view(), name='subscription'),
    path('subscription/price/', SubscriptionPriceView.as_view(), name='subscription-price'),
    
    # ==================== COURSE MANAGEMENT ENDPOINTS ====================
    
    # Course endpoints
    path('courses/', CourseListCreateView.as_view(), name='course-list-create'),
    path('courses/<int:pk>/', CourseDetailView.as_view(), name='course-detail'),
    
    # Syllabus endpoints
    path('syllabi/', SyllabusListCreateView.as_view(), name='syllabus-list-create'),
    path('syllabi/<int:pk>/', SyllabusDetailView.as_view(), name='syllabus-detail'),
    
    # Subject endpoints
    path('subjects/', SubjectListCreateView.as_view(), name='subject-list-create'),
    path('subjects/<int:pk>/', SubjectDetailView.as_view(), name='subject-detail'),
    
    # Chapter endpoints
    path('chapters/', ChapterListCreateView.as_view(), name='chapter-list-create'),
    path('chapters/<int:pk>/', ChapterDetailView.as_view(), name='chapter-detail'),
    
    # Topic endpoints
    path('topics/', TopicListCreateView.as_view(), name='topic-list-create'),
    path('topics/<int:pk>/', TopicDetailView.as_view(), name='topic-detail'),

    # Admin topic processing
    path('admin/process-topics/', AdminProcessTopicBatchView.as_view(), name='admin-process-topics'),
    path('admin/tasks/', AdminTaskListCreateView.as_view(), name='admin-task-list-create'),
    path('admin/tasks/<int:pk>/', AdminTaskDetailView.as_view(), name='admin-task-detail'),
    
    # Admin add items to task
    path('admin/tasks/<int:task_id>/add-video/', AdminAddVideoItemView.as_view(), name='admin-add-video-item'),
    path('admin/tasks/<int:task_id>/add-quiz/', AdminAddQuizItemView.as_view(), name='admin-add-quiz-item'),
    path('admin/tasks/<int:task_id>/add-game/', AdminAddGameItemView.as_view(), name='admin-add-game-item'),
    path('admin/tasks/<int:task_id>/add-activity/', AdminAddActivityItemView.as_view(), name='admin-add-activity-item'),
    
    # Admin approved videos
    path('admin/approved-videos/', AdminApprovedVideosListView.as_view(), name='admin-approved-videos'),
]
