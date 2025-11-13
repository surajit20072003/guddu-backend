# api/urls.py
from django.urls import path
from . import views # Make sure views are imported

urlpatterns = [
    
    # Add this new line
    #path('start-search/', views.StartSearchAPIView.as_view(), name='start-search'),
    path('admin/upload-and-extract/', views.AdminUploadView.as_view(), name='admin-upload'),
    
    # Endpoint 2: For the admin to start the 80-tag batch
    path('admin/start-batch-process/', views.AdminStartBatchView.as_view(), name='admin-start-batch'),

]