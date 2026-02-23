
from rest_framework import serializers
from .models import User, UserProfile, Plan, PlanPricing, Subscription, ProfileSubscription, Course, Syllabus, Subject, Chapter, Topic, Task, TaskItem, TaskVideo, TaskQuiz, TaskGame, TaskActivity,VideoResult

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


# ==================== COURSE SERIALIZERS ===================

class CourseSerializer(serializers.ModelSerializer):
    grade_display = serializers.CharField(source='get_grade_display', read_only=True)
    
    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'grade', 'grade_display', 
                  'thumbnail', 'is_active', 'created_at', 'updated_at']


class SyllabusSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    
    class Meta:
        model = Syllabus
        fields = ['id', 'course', 'course_title', 'title', 'description', 
                  'academic_year', 'is_active', 'created_at', 'updated_at']


class SubjectSerializer(serializers.ModelSerializer):
    syllabus_title = serializers.CharField(source='syllabus.title', read_only=True)
    
    class Meta:
        model = Subject
        fields = ['id', 'syllabus', 'syllabus_title', 'name', 'description', 
                  'order', 'icon', 'is_active', 'created_at', 'updated_at']


class ChapterSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    
    class Meta:
        model = Chapter
        fields = ['id', 'subject', 'subject_name', 'title', 'description', 
                  'chapter_number', 'is_active', 'created_at', 'updated_at']


class TopicSerializer(serializers.ModelSerializer):
    chapter_title = serializers.CharField(source='chapter.title', read_only=True)
    
    class Meta:
        model = Topic
        fields = ['id', 'chapter', 'chapter_title', 'title', 'description', 
                  'order', 'search_status', 'last_searched_at', 'is_active', 
                  'created_at', 'updated_at']
        read_only_fields = ['search_status', 'last_searched_at']



# ==================== VIDEO SERIALIZERS ====================

class VideoResultSerializer(serializers.ModelSerializer):
    """Serializer for video results"""
    class Meta:
        model = VideoResult
        fields = [
            'id', 'title', 'video_id', 'url', 'thumbnail_url',
            'channel_title', 'published_at', 'duration',
            'view_count', 'like_count', 'comment_count',
            'tags_from_video', 'description', 'approval_status', 
            'topic', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'video_id', 'title', 'url', 'thumbnail_url',
            'channel_title', 'published_at', 'duration',
            'view_count', 'like_count', 'comment_count',
            'tags_from_video', 'description', 'created_at', 'updated_at'
        ]


# ==================== TASK ITEM SERIALIZERS ====================

class TaskVideoSerializer(serializers.ModelSerializer):
    video_title = serializers.CharField(source='video.title', read_only=True)
    video_url = serializers.CharField(source='video.url', read_only=True)
    thumbnail_url = serializers.CharField(source='video.thumbnail_url', read_only=True)
    duration = serializers.CharField(source='video.duration', read_only=True)
    channel_title = serializers.CharField(source='video.channel_title', read_only=True)
    
    class Meta:
        model = TaskVideo
        fields = ['id', 'video', 'video_title', 'video_url', 'thumbnail_url', 'duration', 'channel_title']
class TaskQuizSerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField()
    quiz_type_display = serializers.CharField(source='get_quiz_type_display', read_only=True)
    
    class Meta:
        model = TaskQuiz
        fields = ['id', 'quiz_type', 'quiz_type_display', 'questions', 'passing_score', 
                  'time_limit', 'shuffle_questions', 'question_count']
    
    def get_question_count(self, obj):
        return len(obj.questions) if obj.questions else 0
class TaskGameSerializer(serializers.ModelSerializer):
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)
    
    class Meta:
        model = TaskGame
        fields = ['id', 'game_url', 'difficulty', 'difficulty_display', 'instructions']
class TaskActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskActivity
        fields = ['id', 'instructions', 'materials_needed', 'estimated_time', 'image']
class TaskItemSerializer(serializers.ModelSerializer):
    """Serializer for TaskItem (polymorphic)"""
    video_data = TaskVideoSerializer(read_only=True)
    quiz_data = TaskQuizSerializer(read_only=True)
    game_data = TaskGameSerializer(read_only=True)
    activity_data = TaskActivitySerializer(read_only=True)
    
    class Meta:
        model = TaskItem
        fields = ['id', 'task', 'item_type', 'title', 'day_number', 'order', 'is_active', 
                  'video_data', 'quiz_data', 'game_data', 'activity_data', 'created_at']
class TaskSerializer(serializers.ModelSerializer):
    items = TaskItemSerializer(many=True, read_only=True)
    grade = serializers.CharField(read_only=True)  # Comes from topic hierarchy
    topic_title = serializers.CharField(source='topic.title', read_only=True)
    chapter_title = serializers.CharField(source='topic.chapter.title', read_only=True)
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = ['id', 'topic', 'topic_title', 'chapter_title', 'grade', 'title', 'description', 
                  'start_day', 'end_day', 'is_active', 'items', 'item_count', 'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_at', 'updated_at']
    
    def get_item_count(self, obj):
        return obj.items.filter(is_active=True).count()
# Serializers for adding items
class AddVideoItemSerializer(serializers.Serializer):
    """Serializer for adding a video item to a task"""
    video_id = serializers.IntegerField()
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    day_number = serializers.IntegerField(min_value=1, required=True, help_text="Which day this video belongs to")
    order = serializers.IntegerField(default=0)
class AddQuizItemSerializer(serializers.Serializer):
    """Serializer for adding a quiz item to a task"""
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    quiz_type = serializers.ChoiceField(choices=['QUESTION_OPTIONS', 'MATCH_MAKING'], default='QUESTION_OPTIONS')
    questions = serializers.JSONField()
    passing_score = serializers.IntegerField(min_value=0, max_value=100, default=70)
    day_number = serializers.IntegerField(min_value=1, required=True, help_text="Which day this quiz belongs to")
    time_limit = serializers.IntegerField(required=False, allow_null=True)
    shuffle_questions = serializers.BooleanField(default=True)
    order = serializers.IntegerField(default=0)
    
    def validate(self, attrs):
        """Validate questions structure based on quiz_type"""
        quiz_type = attrs.get('quiz_type')
        questions = attrs.get('questions')
        
        if not isinstance(questions, list):
            raise serializers.ValidationError({'questions': 'Questions must be a list'})
        
        if len(questions) == 0:
            raise serializers.ValidationError({'questions': 'At least one question is required'})
        
        if quiz_type == 'QUESTION_OPTIONS':
            # Validate question-options structure
            for idx, q in enumerate(questions):
                if 'question' not in q:
                    raise serializers.ValidationError({
                        'questions': f'Question {idx+1}: "question" field is required'
                    })
                if 'options' not in q:
                    raise serializers.ValidationError({
                        'questions': f'Question {idx+1}: "options" field is required'
                    })
                if 'correct_answer' not in q:
                    raise serializers.ValidationError({
                        'questions': f'Question {idx+1}: "correct_answer" field is required'
                    })
                if not isinstance(q['options'], list) or len(q['options']) < 2:
                    raise serializers.ValidationError({
                        'questions': f'Question {idx+1}: At least 2 options are required'
                    })
        
        elif quiz_type == 'MATCH_MAKING':
            # Validate match-making structure
            for idx, q in enumerate(questions):
                if 'instruction' not in q:
                    raise serializers.ValidationError({
                        'questions': f'Question {idx+1}: "instruction" field is required'
                    })
                if 'pairs' not in q:
                    raise serializers.ValidationError({
                        'questions': f'Question {idx+1}: "pairs" field is required'
                    })
                if 'correct_matches' not in q:
                    raise serializers.ValidationError({
                        'questions': f'Question {idx+1}: "correct_matches" field is required'
                    })
                if not isinstance(q['pairs'], list) or len(q['pairs']) < 2:
                    raise serializers.ValidationError({
                        'questions': f'Question {idx+1}: At least 2 pairs are required'
                    })
                if not isinstance(q['correct_matches'], list):
                    raise serializers.ValidationError({
                        'questions': f'Question {idx+1}: "correct_matches" must be a list'
                    })
        
        return attrs
class AddGameItemSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    game_url = serializers.URLField()
    difficulty = serializers.ChoiceField(choices=['EASY', 'MEDIUM', 'HARD'], default='EASY')
    instructions = serializers.CharField(required=False, allow_blank=True)
    day_number = serializers.IntegerField(min_value=1, required=True, help_text="Which day this game belongs to")
    order = serializers.IntegerField(default=0)
class AddActivityItemSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    instructions = serializers.CharField()
    materials_needed = serializers.CharField(required=False, allow_blank=True)
    estimated_time = serializers.IntegerField()
    day_number = serializers.IntegerField(min_value=1, required=True, help_text="Which day this activity belongs to")
    order = serializers.IntegerField(default=0)


# ==================== QUIZ ANSWER SUBMISSION ====================

class QuizAnswerSerializer(serializers.Serializer):
    """Serializer for quiz answer submission"""
    task_item_id = serializers.IntegerField()
    user_answers = serializers.JSONField(help_text="User's answers - format depends on quiz type")
    time_taken = serializers.IntegerField(required=False, help_text="Time taken in seconds")
    
    def validate_user_answers(self, value):
        """Basic validation for user answers"""
        if not isinstance(value, (list, dict)):
            raise serializers.ValidationError("user_answers must be a list or dict")
        return value
