# api/views.py
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.conf import settings
from django.db import transaction, models
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
        try:
            # Get all active (non-cancelled) letters
            active_letters = Letter.objects.filter(is_cancelled=False)
            active_numbers = set(active_letters.values_list('number', flat=True))
            
            # Find the lowest available cancelled letter number that's not currently in use
            available_cancelled = Letter.objects.filter(
                is_cancelled=True
            ).exclude(
                number__in=active_numbers
            ).order_by('number').first()

            if available_cancelled:
                new_number = available_cancelled.number
                print(f"Reusing cancelled letter number: {new_number}")
            else:
                # No cancelled numbers available, get the next sequential number
                if active_letters.exists():
                    max_active_number = active_letters.aggregate(
                        max_num=models.Max('number')
                    )['max_num']
                    new_number = max_active_number + 1
                else:
                    # No active letters at all, start from 301
                    new_number = 301
                print(f"Using next sequential number: {new_number}")

            print(f"Attempting to create letter with number: {new_number}")
            print(f"User: {self.request.user.username}")
            print(f"Serializer data: {serializer.validated_data}")

            # Check if this number already exists and is active
            existing_active = Letter.objects.filter(number=new_number, is_cancelled=False).exists()
            if existing_active:
                raise ValueError(f"Number {new_number} is already in use by an active letter")

            # Save with the computed number and authenticated user's username
            letter = serializer.save(
                number=new_number,
                registered_by_username=self.request.user.username
            )
            
            print(f"Successfully created letter: {letter}")
            return letter
            
        except Exception as e:
            # Log the actual error for debugging
            print(f"Error in perform_create: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            raise e

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