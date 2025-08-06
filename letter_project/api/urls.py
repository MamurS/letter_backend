# api/urls.py
from django.urls import path
from .views import (
    LetterListCreateAPIView, 
    LetterCancelAPIView, 
    LetterRestoreAPIView,
    SignUpAPIView,
    PasswordResetRequestAPIView,
    PasswordResetConfirmAPIView
)

urlpatterns = [
    # e.g., GET /api/letters/ or POST /api/letters/
    path('letters/', LetterListCreateAPIView.as_view(), name='letter-list-create'),
    
    # e.g., POST /api/letters/305/cancel/
    path('letters/<int:pk>/cancel/', LetterCancelAPIView.as_view(), name='letter-cancel'),
    
    # e.g., POST /api/letters/306/restore/
    path('letters/<int:pk>/restore/', LetterRestoreAPIView.as_view(), name='letter-restore'),

    # ... your existing letter paths
    path('signup/', SignUpAPIView.as_view(), name='signup'),
    path('password-reset/', PasswordResetRequestAPIView.as_view(), name='password-reset-request'),
    path('password-reset/<uidb64>/<token>/', PasswordResetConfirmAPIView.as_view(), name='password-reset-confirm'),
]
