# api/views.py
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.conf import settings
from django.db import transaction
from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Letter
from .serializers import SignUpSerializer, PasswordResetSerializer, LetterSerializer

class LetterListCreateAPIView(generics.ListCreateAPIView):
    """
    API endpoint for listing all letters and creating a new one.
    """
    queryset = Letter.objects.all()
    serializer_class = LetterSerializer
    permission_classes = [IsAuthenticated] # Ensures only logged-in users can access

    @transaction.atomic
    def perform_create(self, serializer):
        # Find all numbers currently used by active letters
        active_numbers = set(Letter.objects.filter(is_cancelled=False).values_list('number', flat=True))
        
        # Find the oldest cancelled letter whose number is not currently in use
        available_cancelled = Letter.objects.filter(is_cancelled=True).exclude(number__in=active_numbers).order_by('number')

        if available_cancelled.exists():
            new_number = available_cancelled.first().number
        else:
            # Find the highest number in the entire table to determine the next one
            last_letter = Letter.objects.order_by('number').last()
            new_number = (last_letter.number + 1) if last_letter else 301

        # **FIXED**: Use the authenticated user's username from the request
        serializer.save(
            number=new_number,
            registered_by_username=self.request.user.username
        )

class LetterCancelAPIView(views.APIView):
    """
    API endpoint to cancel a letter.
    """
    permission_classes = [IsAuthenticated] # Ensures only logged-in users can access
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
    """
    permission_classes = [IsAuthenticated] # Ensures only logged-in users can access
    def post(self, request, pk):
        try:
            letter_to_restore = Letter.objects.get(pk=pk, is_cancelled=True)
            
            is_reused = Letter.objects.filter(number=letter_to_restore.number, is_cancelled=False).exists()
            if is_reused:
                return Response({"error": "This number has already been reassigned."}, status=status.HTTP_409_CONFLICT)
            
            letter_to_restore.is_cancelled = False
            letter_to_restore.save()
            return Response(status=status.HTTP_200_OK)

        except Letter.DoesNotExist:
            return Response({"error": "Cancelled letter not found."}, status=status.HTTP_404_NOT_FOUND)


# --- Authentication Views ---

class SignUpAPIView(generics.GenericAPIView):
    serializer_class = SignUpSerializer
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
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # IMPORTANT: Update with your frontend URL
            reset_link = f"https://letter-frontend-gzp7.onrender.com/reset-password/{uid}/{token}/" 
            
            send_mail(
                'Password Reset for LetterApp',
                f'Hello,\n\nPlease click the link below to reset your password:\n\n{reset_link}\n\nIf you did not request this, please ignore this email.',
                settings.DEFAULT_FROM_EMAIL,
                [email],
            )
            return Response({"message": "Password reset link sent."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)

class PasswordResetConfirmAPIView(views.APIView):
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
            return Response({"error": "Invalid token or user."}, status=status.HTTP_400_BAD_REQUEST)
