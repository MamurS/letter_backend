# api/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Letter # Import the Letter model
import re

class LetterSerializer(serializers.ModelSerializer):
    """
    Serializer for the Letter model. Converts Letter objects to JSON and back.
    """
    class Meta:
        model = Letter
        fields = [
            'id', 
            'number', 
            'subject', 
            'addressee', 
            'registered_by_username', 
            'registered_at', 
            'isCancelled'
        ]
        # **FIXED**: 'registered_by_username' is no longer read-only
        read_only_fields = ['id', 'number', 'registered_at']

    # Use a read_only field to represent the model's 'is_cancelled' field
    isCancelled = serializers.BooleanField(source='is_cancelled', read_only=True)


class SignUpSerializer(serializers.Serializer):
    """
    Serializer for validating the sign-up email.
    """
    email = serializers.EmailField()

    def validate_email(self, value):
        if not re.match(r"^[a-zA-Z0-9\.\+_-]+@mosaic-insurance\.com$", value):
            raise serializers.ValidationError("Invalid email format. Must be a 'mosaic-insurance.com' address.")
        
        username = value.split('@')[0]
        if User.objects.filter(email=value).exists() or User.objects.filter(username=username).exists():
            raise serializers.ValidationError("A user with this email or username already exists.")
            
        return value

class PasswordResetSerializer(serializers.Serializer):
    """
    Serializer for confirming a password reset.
    """
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    password2 = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data
