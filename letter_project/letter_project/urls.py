# letter_project/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # 1. Django Admin site
    path('admin/', admin.site.urls),
    
    # 2. Your application's API endpoints (from api/urls.py)
    path('api/', include('api.urls')), 
    
    # 3. JWT Token Endpoints for Login and Refresh
    # The frontend will send a POST request with username and password to this URL
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    
    # The frontend can use this endpoint to get a new access token
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

