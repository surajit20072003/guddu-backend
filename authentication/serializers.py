
from rest_framework import serializers
from .models import User,UserProfile

class UserRegistrationSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True, required=True, label="Confirm Password")

    class Meta:
        model = User
        fields = ('email', 'password', 'password2')
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        attrs.pop('password2')
        return attrs
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Handles serialization for the UserProfile model.
    The 'user' field is excluded because it's set in the view.
    """
    class Meta:
        model = UserProfile
        # We list all fields from the UserProfile model that the app can send
        fields = (
            'full_name', 'profile_picture', 'mother_tongue', 'age', 'is_below_class_5',
            'is_studying', 'reason_not_studying', 'school_type', 'school_name',
            'grade', 'country', 'state', 'city', 'plan'
        )