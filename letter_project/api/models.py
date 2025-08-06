# api/models.py
from django.db import models
from django.contrib.auth.models import User # Using Django's built-in User model

class Letter(models.Model):
    """
    Represents a registered letter in the database.
    """
    number = models.PositiveIntegerField(unique=True, help_text="The unique registration number of the letter.")
    subject = models.CharField(max_length=255, help_text="The subject of the letter.")
    addressee = models.CharField(max_length=255, help_text="The name of the letter's addressee (e.g., NAPP).")
    
    # In a real system, this would be a ForeignKey to the logged-in user.
    # We use a CharField to match the mock data's 'registered_by_username'.
    registered_by_username = models.CharField(max_length=150, help_text="Username of the person who registered the letter.")
    
    registered_at = models.DateTimeField(auto_now_add=True, help_text="The exact date and time the letter was registered.")
    is_cancelled = models.BooleanField(default=False, help_text="True if the letter has been cancelled.")

    class Meta:
        ordering = ['-number'] # Default order is newest first

    def __str__(self):
        status = "CANCELLED" if self.is_cancelled else "Active"
        return f"No. {self.number} - {self.addressee} ({status})"

# Create your models here.
