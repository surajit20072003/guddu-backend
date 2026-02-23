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
    
    # ==================== COURSE MANAGEMENT ENDPOINTS (ADMIN) ====================
    
    # Course endpoints (Admin)
    path('admin/courses/', CourseListCreateView.as_view(), name='course-list-create'),
    path('admin/courses/<int:pk>/', CourseDetailView.as_view(), name='course-detail'),
    
    # Syllabus endpoints (Admin)
    path('admin/syllabi/', SyllabusListCreateView.as_view(), name='syllabus-list-create'),
    path('admin/syllabi/<int:pk>/', SyllabusDetailView.as_view(), name='syllabus-detail'),
    
    # Subject endpoints (Admin)
    path('admin/subjects/', SubjectListCreateView.as_view(), name='subject-list-create'),
    path('admin/subjects/<int:pk>/', SubjectDetailView.as_view(), name='subject-detail'),
    
    # Chapter endpoints (Admin)
    path('admin/chapters/', ChapterListCreateView.as_view(), name='chapter-list-create'),
    path('admin/chapters/<int:pk>/', ChapterDetailView.as_view(), name='chapter-detail'),
    
    # Topic endpoints (Admin)
    path('admin/topics/', TopicListCreateView.as_view(), name='topic-list-create'),
    path('admin/topics/<int:pk>/', TopicDetailView.as_view(), name='topic-detail'),

    # Admin topic processing
    path('admin/process-topics/', AdminProcessTopicBatchView.as_view(), name='admin-process-topics'),
    
    # Task management (Admin)
    path('admin/tasks/', AdminTaskListCreateView.as_view(), name='admin-task-list-create'),
    path('admin/tasks/<int:pk>/', AdminTaskDetailView.as_view(), name='admin-task-detail'),
    
    # Admin add items to task
    path('admin/tasks/<int:task_id>/add-video/', AdminAddVideoItemView.as_view(), name='admin-add-video-item'),
    path('admin/tasks/<int:task_id>/add-quiz/', AdminAddQuizItemView.as_view(), name='admin-add-quiz-item'),
    path('admin/tasks/<int:task_id>/add-game/', AdminAddGameItemView.as_view(), name='admin-add-game-item'),
    path('admin/tasks/<int:task_id>/add-activity/', AdminAddActivityItemView.as_view(), name='admin-add-activity-item'),
    
    # Admin edit items in task
    path('admin/tasks/video/<int:task_item_id>/edit/', AdminEditVideoItemView.as_view(), name='admin-edit-video-item'),
    path('admin/tasks/quiz/<int:task_item_id>/edit/', AdminEditQuizItemView.as_view(), name='admin-edit-quiz-item'),
    path('admin/tasks/game/<int:task_item_id>/edit/', AdminEditGameItemView.as_view(), name='admin-edit-game-item'),
    path('admin/tasks/activity/<int:task_item_id>/edit/', AdminEditActivityItemView.as_view(), name='admin-edit-activity-item'),

    
    # Admin video management
    path('admin/videos/', VideoListView.as_view(), name='video-list'),
    path('admin/videos/<int:pk>/', VideoDetailView.as_view(), name='video-detail'),
    path('admin/videos/<int:pk>/approve/', VideoApproveView.as_view(), name='video-approve'),
    path('admin/videos/<int:pk>/disapprove/', VideoDisapproveView.as_view(), name='video-disapprove'),
    path('admin/approved-videos/', AdminApprovedVideosListView.as_view(), name='admin-approved-videos'),
    
    # Quiz answer submission (Student/User)
    path('submit-quiz-answer/', SubmitQuizAnswerView.as_view(), name='submit-quiz-answer'),
]

