# authentication/urls.py

from django.urls import path
from .views import RegisterView, LoginView, LogoutView,ProfileView
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
    path('profile/', ProfileView.as_view(), name='user-profile')
]