from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from . import enums 


from .managers import CustomUserManager

class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = [] 
    objects = CustomUserManager()

    def __str__(self):
        return self.email
    


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Screen: Profile Picture
    full_name = models.CharField(max_length=100, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    mother_tongue = models.CharField(max_length=50, choices=enums.MotherTongue.choices, blank=True)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    is_below_class_5 = models.BooleanField(default=False)

    # Screen: Are you studying in school?
    is_studying = models.BooleanField(null=True) # User's choice: Yes/No
    
    # -- If 'is_studying' is False --
    reason_not_studying = models.TextField(blank=True, help_text="Reason if user is not in school")

    # -- If 'is_studying' is True --
    school_type = models.CharField(max_length=20, choices=enums.SchoolType.choices, blank=True)
    school_name = models.CharField(max_length=255, blank=True)
    grade = models.CharField(max_length=10, choices=enums.Grade.choices, blank=True)
    country = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)

    # Screen: Select Plan
    plan = models.CharField(max_length=10, choices=enums.Plan.choices, default=enums.Plan.FREE)

    def __str__(self):
        return f"{self.user.username}'s Profile"

