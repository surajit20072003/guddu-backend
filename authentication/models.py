from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal
from . import enums 


from .managers import CustomUserManager

class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True, null=True, blank=True)
    mobile = models.CharField(max_length=15, unique=True, null=True, blank=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = [] 
    objects = CustomUserManager()

    def clean(self):
        super().clean()
        if not self.email and not self.mobile:
            from django.core.exceptions import ValidationError
            raise ValidationError('Either email or mobile number must be provided.')

    def __str__(self):
        return self.email or self.mobile or str(self.id)
    


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Screen: Account For
    account_for = models.CharField(max_length=10, choices=enums.AccountFor.choices)
    
    # Screen: Profile Picture
    full_name = models.CharField(max_length=100)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True)
    mother_tongue = models.CharField(max_length=50, choices=enums.MotherTongue.choices)
    age = models.CharField(max_length=5, choices=enums.ChildAge.choices, help_text="Child's age (2.0 to 6.0 years)")

    # Screen: Are you studying in school?
    is_studying = models.BooleanField() # User's choice: Yes/No
    
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
    
    # Subscription relationship (for MASTER plan - multiple profiles can share one subscription)
    subscription = models.ForeignKey('Subscription', on_delete=models.SET_NULL, null=True, blank=True, related_name='profiles')

    def __str__(self):
        return f"{self.user.email or self.user.mobile or self.user.id}'s Profile"


class Plan(models.Model):
    """
    Plan model stores all plan features and settings.
    """
    name = models.CharField(max_length=10, choices=enums.Plan.choices, unique=True)
    display_name = models.CharField(max_length=50)
    
    # Features
    course_content_percentage = models.IntegerField(help_text="Percentage of course content accessible (60 for FREE, 100 for others)")
    has_activities = models.BooleanField(default=False)
    has_quizzes = models.BooleanField(default=False)
    has_games = models.BooleanField(default=False)
    shows_ads = models.BooleanField(default=True)
    allows_multiple_profiles = models.BooleanField(default=False)
    
    # Pricing settings
    master_discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Discount amount for MASTER plan (₹20 default)"
    )
    yearly_discount_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Percentage discount for yearly subscriptions (for future use)"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.display_name


class PlanPricing(models.Model):
    """
    Grade-based pricing for JUNIOR plan.
    Stores monthly and yearly prices for each grade (Nursery, LKG, UKG).
    """
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='pricing')
    grade = models.CharField(max_length=10, choices=enums.Grade.choices)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monthly price in ₹")
    yearly_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Yearly price in ₹ (calculated: monthly * 12)")
    
    # For future discount support
    yearly_discount_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Percentage discount for yearly subscription (for future use)"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['plan', 'grade']
        ordering = ['plan', 'grade']
    
    def save(self, *args, **kwargs):
        # Auto-calculate yearly price if not set
        if not self.yearly_price:
            self.yearly_price = self.monthly_price * Decimal('12')
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.plan.display_name} - {self.get_grade_display()} (₹{self.monthly_price}/month)"


class Subscription(models.Model):
    """
    User subscription model.
    One user can have one active subscription at a time.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='subscriptions')
    
    # Duration
    duration = models.CharField(max_length=10, choices=enums.SubscriptionDuration.choices)
    
    # Status
    status = models.CharField(max_length=10, choices=enums.SubscriptionStatus.choices, default=enums.SubscriptionStatus.PENDING)
    
    # Dates
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    renewal_date = models.DateTimeField(null=True, blank=True, help_text="Next renewal date for auto-renewal")
    
    # Settings
    is_auto_renew = models.BooleanField(default=True)
    
    # Pricing (stored for record)
    monthly_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monthly amount for this subscription")
    total_amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # For JUNIOR plan - store the grade used for pricing
    pricing_grade = models.CharField(
        max_length=10, 
        choices=enums.Grade.choices, 
        null=True, 
        blank=True,
        help_text="Grade used for pricing (Nursery/LKG/UKG for JUNIOR plan)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def is_active_subscription(self):
        """Check if subscription is currently active"""
        return (
            self.status == enums.SubscriptionStatus.ACTIVE and 
            self.end_date and 
            self.end_date > timezone.now()
        )
    
    def can_access_full_content(self):
        """Check if user can access full course content"""
        return self.plan.course_content_percentage == 100
    
    def can_access_activities(self):
        """Check if user can access activities"""
        return self.plan.has_activities
    
    def can_access_quizzes(self):
        """Check if user can access quizzes"""
        return self.plan.has_quizzes
    
    def can_access_games(self):
        """Check if user can access games"""
        return self.plan.has_games
    
    def should_show_ads(self):
        """Check if ads should be shown"""
        return self.plan.shows_ads
    
    def can_create_multiple_profiles(self):
        """Check if user can create multiple profiles"""
        return self.plan.allows_multiple_profiles
    
    def __str__(self):
        return f"{self.user.email or self.user.mobile or self.user.id} - {self.plan.display_name} ({self.get_status_display()})"


class ProfileSubscription(models.Model):
    """
    Links profiles to MASTER plan subscriptions.
    Tracks which profiles are included in a MASTER subscription for pricing calculation.
    """
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='profile_subscriptions')
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='profile_subscription')
    grade = models.CharField(max_length=10, choices=enums.Grade.choices, help_text="Grade for pricing calculation (Nursery/LKG/UKG)")
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monthly price for this profile's grade")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['subscription', 'profile']
        ordering = ['subscription', 'created_at']
    
    def __str__(self):
        return f"{self.subscription} - {self.profile.full_name} ({self.get_grade_display()})"

