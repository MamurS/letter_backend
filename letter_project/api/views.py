# api/views.py
from django.db import transaction
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.conf import settings
from rest_framework import generics, status, views, permissions
from rest_framework.response import Response
from .models import Letter
from .serializers import LetterSerializer, SignUpSerializer, PasswordResetSerializer

# --- Letter Management Views (Protected) ---

class LetterListCreateAPIView(generics.ListCreateAPIView):
    """
    API endpoint for listing all letters and creating a new one.
    - GET /api/letters/: Returns a list of all letters.
    - POST /api/letters/: Creates a new letter.
    Requires authentication.
    """
    queryset = Letter.objects.all()
    serializer_class = LetterSerializer
    permission_classes = [permissions.IsAuthenticated] # Ensures only logged-in users can access

    def get_queryset(self):
        """
        Return a sorted queryset.
        - Primary sort: by number descending.
        - Secondary sort: by active status (active letters first).
        - Tertiary sort: by date descending (newest first).
        """
        return Letter.objects.all().order_by('-number', 'is_cancelled', '-registered_at')

    @transaction.atomic
    def perform_create(self, serializer):
        # Find active numbers to avoid reusing them
        active_numbers = set(Letter.objects.filter(is_cancelled=False).values_list('number', flat=True))
        
        # Find the lowest available number from cancelled letters that is not active
        available_cancelled = Letter.objects.filter(
            is_cancelled=True
        ).exclude(
            number__in=active_numbers
        ).order_by('number').first()

        if available_cancelled:
            new_number = available_cancelled.number
        else:
            last_letter = Letter.objects.order_by('number').last()
            new_number = (last_letter.number + 1) if last_letter else 301

        serializer.save(
            number=new_number,
            registered_by_username=self.request.user.username
        )

class LetterCancelAPIView(views.APIView):
    """
    API endpoint to cancel a letter.
    - POST /api/letters/<int:pk>/cancel/: Marks a letter as cancelled.
    Requires authentication.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            letter = Letter.objects.get(pk=pk)
            letter.is_cancelled = True
            letter.save()
            return Response(status=status.HTTP_200_OK)
        except Letter.DoesNotExist:
            return Response({"error": "Letter not found."}, status=status.HTTP_404_NOT_FOUND)

class LetterRestoreAPIView(views.APIView):
    """
    API endpoint to restore a cancelled letter.
    - POST /api/letters/<int:pk>/restore/: Restores a letter if its number is not in use.
    Requires authentication.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            letter_to_restore = Letter.objects.get(pk=pk, is_cancelled=True)
            
            is_reused = Letter.objects.filter(number=letter_to_restore.number, is_cancelled=False).exists()
            if is_reused:
                return Response({"detail": "This number has already been reassigned."}, status=status.HTTP_409_CONFLICT)
            
            letter_to_restore.is_cancelled = False
            letter_to_restore.save()
            return Response(status=status.HTTP_200_OK)

        except Letter.DoesNotExist:
            return Response({"error": "Cancelled letter not found."}, status=status.HTTP_404_NOT_FOUND)


# --- Authentication Views (Public) ---

class SignUpAPIView(generics.GenericAPIView):
    """
    API endpoint for signing up a new user.
    """
    serializer_class = SignUpSerializer
    permission_classes = [permissions.AllowAny] # Anyone can sign up

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        username = email.split('@')[0]
        
        password = User.objects.make_random_password()
        user = User.objects.create_user(username=username, email=email, password=password)
        
        send_mail(
            'Your Login Credentials for LetterApp',
            f'Hello,\n\nYour account has been created.\n\nUsername: {username}\nPassword: {password}\n\nPlease change your password after your first login.\n\nThank you!',
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        
        return Response({"message": f"Credentials sent to email {email}"}, status=status.HTTP_201_CREATED)

class PasswordResetRequestAPIView(views.APIView):
    """
    API endpoint to request a password reset link.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # TODO: Update with your frontend URL in production
            reset_link = f"http://localhost:5173/reset-password/{uid}/{token}/" 
            
            send_mail(
                'Password Reset for LetterApp',
                f'Hello,\n\nPlease click the link below to reset your password:\n\n{reset_link}\n\nIf you did not request this, please ignore this email.',
                settings.DEFAULT_FROM_EMAIL,
                [email],
            )
            return Response({"message": "Password reset link sent."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"detail": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)

class PasswordResetConfirmAPIView(views.APIView):
    """
    API endpoint to confirm and set the new password.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, uidb64, token, *args, **kwargs):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            user.set_password(serializer.validated_data['password'])
            user.save()
            return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "Invalid token or user."}, status=status.HTTP_400_BAD_REQUEST)