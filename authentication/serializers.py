
from rest_framework import serializers
from .models import User, UserProfile, Plan, PlanPricing, Subscription, ProfileSubscription

class UserRegistrationSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True, required=True, label="Confirm Password")
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    mobile = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=15)

    class Meta:
        model = User
        fields = ('email', 'mobile', 'password', 'password2')
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate_email(self, value):
        """Validate email uniqueness if provided"""
        if value:
            value = value.lower().strip()
            if User.objects.filter(email=value).exists():
                raise serializers.ValidationError("User with this email already exists.")
        return value
    
    def validate_mobile(self, value):
        """Validate mobile format and uniqueness if provided"""
        if value:
            # Remove non-digit characters for validation
            mobile_clean = ''.join(filter(str.isdigit, value))
            if len(mobile_clean) < 10 or len(mobile_clean) > 15:
                raise serializers.ValidationError("Mobile number must be between 10 and 15 digits.")
            if User.objects.filter(mobile=mobile_clean).exists():
                raise serializers.ValidationError("User with this mobile number already exists.")
            return mobile_clean
        return value

    def validate(self, attrs):
        email = attrs.get('email', '').strip() if attrs.get('email') else ''
        mobile = attrs.get('mobile', '').strip() if attrs.get('mobile') else ''
        
        # At least one of email or mobile must be provided
        if not email and not mobile:
            raise serializers.ValidationError({
                "error": "Either email or mobile number is required."
            })
        
        # Validate password match
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        # Clean email if provided
        if email:
            attrs['email'] = email.lower().strip()
        
        attrs.pop('password2')
        return attrs
    
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Handles serialization for the UserProfile model.
    The 'user' field is excluded because it's set in the view.
    Fields up to and including 'is_studying' are required, fields after 'is_studying' are optional.
    """
    class Meta:
        model = UserProfile
        # We list all fields from the UserProfile model that the app can send
        fields = (
            'account_for', 'full_name', 'profile_picture', 'mother_tongue', 'age',
            'is_studying', 'reason_not_studying', 'school_type', 'school_name',
            'grade', 'country', 'state', 'city', 'plan'
        )
        extra_kwargs = {
            # Required fields (before is_studying)
            'account_for': {'required': True},
            'full_name': {'required': True},
            'profile_picture': {'required': False, 'allow_null': True},
            'mother_tongue': {'required': True},
            'age': {'required': True},
            'is_studying': {'required': True},
            # Optional fields (after is_studying)
            'reason_not_studying': {'required': False},
            'school_type': {'required': False},
            'school_name': {'required': False},
            'grade': {'required': False},
            'country': {'required': False},
            'state': {'required': False},
            'city': {'required': False},
            'plan': {'required': False},
        }


class PlanPricingSerializer(serializers.ModelSerializer):
    """Serializer for PlanPricing model"""
    grade_display = serializers.CharField(source='get_grade_display', read_only=True)
    
    class Meta:
        model = PlanPricing
        fields = ('id', 'grade', 'grade_display', 'monthly_price', 'yearly_price', 'yearly_discount_percentage', 'is_active')
        read_only_fields = ('id', 'yearly_price')


class PlanSerializer(serializers.ModelSerializer):
    """Serializer for Plan model"""
    pricing = serializers.SerializerMethodField()
    
    def get_pricing(self, obj):
        """Get active pricing for this plan"""
        active_pricing = obj.pricing.filter(is_active=True)
        return PlanPricingSerializer(active_pricing, many=True).data
    
    class Meta:
        model = Plan
        fields = (
            'id', 'name', 'display_name', 'course_content_percentage',
            'has_activities', 'has_quizzes', 'has_games', 'shows_ads',
            'allows_multiple_profiles', 'master_discount_amount',
            'yearly_discount_percentage', 'is_active', 'pricing'
        )
        read_only_fields = ('id',)


class ProfileSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for ProfileSubscription model"""
    profile_name = serializers.CharField(source='profile.full_name', read_only=True)
    grade_display = serializers.CharField(source='get_grade_display', read_only=True)
    
    class Meta:
        model = ProfileSubscription
        fields = ('id', 'profile', 'profile_name', 'grade', 'grade_display', 'monthly_price')
        read_only_fields = ('id', 'profile_name', 'grade_display', 'monthly_price')


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for Subscription model"""
    plan_details = PlanSerializer(source='plan', read_only=True)
    pricing_grade_display = serializers.CharField(source='get_pricing_grade_display', read_only=True)
    duration_display = serializers.CharField(source='get_duration_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    profile_subscriptions = ProfileSubscriptionSerializer(many=True, read_only=True)
    is_active = serializers.SerializerMethodField()
    
    class Meta:
        model = Subscription
        fields = (
            'id', 'plan', 'plan_details', 'duration', 'duration_display',
            'status', 'status_display', 'start_date', 'end_date', 'renewal_date',
            'is_auto_renew', 'monthly_amount', 'total_amount_paid',
            'pricing_grade', 'pricing_grade_display', 'profile_subscriptions',
            'is_active', 'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'plan_details', 'duration_display', 'status_display',
            'pricing_grade_display', 'profile_subscriptions', 'is_active',
            'created_at', 'updated_at'
        )
    
    def get_is_active(self, obj):
        """Check if subscription is currently active"""
        return obj.is_active_subscription()


class SubscriptionCreateSerializer(serializers.Serializer):
    """Serializer for creating a new subscription"""
    plan = serializers.ChoiceField(choices=['FREE', 'JUNIOR', 'MASTER'])
    duration = serializers.ChoiceField(choices=['MONTHLY', 'YEARLY'])
    grade = serializers.ChoiceField(
        choices=['NURSERY', 'LKG', 'UKG'],
        required=False,
        help_text="Required for JUNIOR plan"
    )
    profile_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of profile IDs. Required for MASTER plan"
    )
    
    def validate(self, attrs):
        plan = attrs.get('plan')
        grade = attrs.get('grade')
        profile_ids = attrs.get('profile_ids', [])
        
        if plan == 'JUNIOR':
            if not grade:
                raise serializers.ValidationError({
                    'grade': 'Grade is required for JUNIOR plan'
                })
            if grade not in ['NURSERY', 'LKG', 'UKG']:
                raise serializers.ValidationError({
                    'grade': 'Grade must be NURSERY, LKG, or UKG for JUNIOR plan'
                })
        
        if plan == 'MASTER':
            if not profile_ids:
                raise serializers.ValidationError({
                    'profile_ids': 'At least one profile ID is required for MASTER plan'
                })
            if len(profile_ids) == 0:
                raise serializers.ValidationError({
                    'profile_ids': 'At least one profile ID is required for MASTER plan'
                })
        
        return attrs


class SubscriptionPriceSerializer(serializers.Serializer):
    """Serializer for calculating subscription price"""
    plan = serializers.ChoiceField(choices=['FREE', 'JUNIOR', 'MASTER'])
    duration = serializers.ChoiceField(choices=['MONTHLY', 'YEARLY'])
    grade = serializers.ChoiceField(
        choices=['NURSERY', 'LKG', 'UKG'],
        required=False,
        help_text="Required for JUNIOR plan"
    )
    profile_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of profile IDs. Required for MASTER plan"
    )
    
    def validate(self, attrs):
        plan = attrs.get('plan')
        grade = attrs.get('grade')
        profile_ids = attrs.get('profile_ids', [])
        
        if plan == 'JUNIOR':
            if not grade:
                raise serializers.ValidationError({
                    'grade': 'Grade is required for JUNIOR plan'
                })
        
        if plan == 'MASTER':
            if not profile_ids or len(profile_ids) == 0:
                raise serializers.ValidationError({
                    'profile_ids': 'At least one profile ID is required for MASTER plan'
                })
        
        return attrs