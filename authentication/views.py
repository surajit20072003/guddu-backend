
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from .serializers import (
    UserRegistrationSerializer, UserProfileSerializer,
    PlanSerializer, SubscriptionSerializer, SubscriptionCreateSerializer,
    SubscriptionPriceSerializer,
    CourseSerializer, SyllabusSerializer, SubjectSerializer, ChapterSerializer, TopicSerializer,TaskSerializer,AddVideoItemSerializer,TaskItemSerializer,AddQuizItemSerializer
)
from .models import User, UserProfile, Plan, Subscription, Course, Syllabus, Subject, Chapter, Topic,Task,TaskItem,TaskVideo,TaskQuiz,TaskGame,TaskActivity,VideoResult
from .utils import calculate_subscription_price, create_subscription, validate_profile_limits
from django.utils import timezone
import threading

class RegisterView(APIView):
    """
    Handles new user registration using either email or mobile with password.
    """
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                refresh = RefreshToken.for_user(user)
                
                user_data = {
                    'id': user.id,
                }
                if user.email:
                    user_data['email'] = user.email
                if user.mobile:
                    user_data['mobile'] = user.mobile
                
                return Response({
                    'message': 'User registered successfully',
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': user_data
                }, status=status.HTTP_201_CREATED)
            except ValidationError as e:
                # Handle model-level validation errors
                error_dict = {}
                if hasattr(e, 'message_dict'):
                    error_dict = e.message_dict
                elif hasattr(e, 'messages'):
                    error_dict = {'error': e.messages}
                else:
                    error_dict = {'error': str(e)}
                return Response(error_dict, status=status.HTTP_400_BAD_REQUEST)
            except IntegrityError as e:
                # Handle database integrity errors (e.g., duplicate email/mobile)
                error_message = str(e)
                if 'email' in error_message.lower():
                    return Response({'email': ['User with this email already exists.']}, status=status.HTTP_400_BAD_REQUEST)
                elif 'mobile' in error_message.lower():
                    return Response({'mobile': ['User with this mobile number already exists.']}, status=status.HTTP_400_BAD_REQUEST)
                return Response({'error': 'A user with this information already exists.'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    Handles user login using either email or mobile with password.
    """
    permission_classes = [AllowAny]
    def post(self, request):
        email = request.data.get('email', '').strip() if request.data.get('email') else ''
        mobile = request.data.get('mobile', '').strip() if request.data.get('mobile') else ''
        password = request.data.get('password')

        if not password:
            return Response({'error': 'Password is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not email and not mobile:
            return Response({'error': 'Either email or mobile number is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Try to find user by email or mobile
        user = None
        if email:
            try:
                user = User.objects.get(email=email.lower())
            except User.DoesNotExist:
                pass
        
        if not user and mobile:
            # Clean mobile number
            mobile_clean = ''.join(filter(str.isdigit, mobile))
            try:
                user = User.objects.get(mobile=mobile_clean)
            except User.DoesNotExist:
                pass
        
        if user is None:
            return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Authenticate the user with password
        if not user.check_password(password):
            return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        user_data = {
            'id': user.id,
            'is_staff': user.is_staff,         
            'is_superuser': user.is_superuser
        }
        if user.email:
            user_data['email'] = user.email
        if user.mobile:
            user_data['mobile'] = user.mobile
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': user_data
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    User logout view.
    Accepts POST requests with a 'refresh' token to blacklist it.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({"error": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate and blacklist the token
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
                return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)
            except TokenError as e:
                return Response({"error": f"Invalid token: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
            except AttributeError:
                # Token blacklist app might not be configured
                return Response({"message": "Successfully logged out. (Token blacklist not configured)"}, status=status.HTTP_200_OK)
        except KeyError:
            return Response({"error": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Logout failed: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        


class ProfileView(APIView):
    """
    Manages the user profile.
    GET: Fetches the profile.
    POST: Creates the profile for the first time.
    PUT: Updates the existing profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Fetch the user's profile."""
        try:
            profile = request.user.profile
            serializer = UserProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserProfile.DoesNotExist:
            # This is normal for a new user, the app will know to create a profile
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        """Create the user's profile (should only be done once)."""
        # Check if a profile already exists to prevent duplicates
        if hasattr(request.user, 'profile'):
            return Response({"error": "Profile already exists. Use PUT to update."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = UserProfileSerializer(data=request.data)
        if serializer.is_valid():
            # Get plan from request data (defaults to FREE)
            plan_name = serializer.validated_data.get('plan', 'FREE')
            
            # Validate profile limits based on plan
            validation = validate_profile_limits(request.user, plan_name)
            if not validation['can_create']:
                return Response(
                    {'error': validation['message']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Securely assign the profile to the currently logged-in user
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """Update the existing user profile."""
        try:
            profile = request.user.profile
            # The 'partial=True' allows for partial updates (PATCH functionality)
            serializer = UserProfileSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except UserProfile.DoesNotExist:
            return Response({"detail": "Profile not found. Use POST to create one first."}, status=status.HTTP_404_NOT_FOUND)


class PlanListView(APIView):
    """
    List all available plans with their features and pricing.
    GET /api/auth/plans/
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Get all active plans"""
        plans = Plan.objects.filter(is_active=True).order_by('name')
        serializer = PlanSerializer(plans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PlanDetailView(APIView):
    """
    Get details of a specific plan.
    GET /api/auth/plans/{id}/
    """
    permission_classes = [AllowAny]
    
    def get(self, request, pk):
        """Get plan details by ID"""
        try:
            plan = Plan.objects.get(pk=pk, is_active=True)
            serializer = PlanSerializer(plan)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Plan.DoesNotExist:
            return Response({"detail": "Plan not found."}, status=status.HTTP_404_NOT_FOUND)


class SubscriptionView(APIView):
    """
    Manage user subscriptions.
    GET: Get current active subscription
    POST: Create a new subscription
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get user's active subscription"""
        try:
            subscription = Subscription.objects.get(
                user=request.user,
                status='ACTIVE',
                end_date__gt=timezone.now()
            )
            serializer = SubscriptionSerializer(subscription)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Subscription.DoesNotExist:
            return Response({"detail": "No active subscription found."}, status=status.HTTP_404_NOT_FOUND)
        except Subscription.MultipleObjectsReturned:
            # Handle edge case where multiple active subscriptions exist
            subscription = Subscription.objects.filter(
                user=request.user,
                status='ACTIVE',
                end_date__gt=timezone.now()
            ).first()
            serializer = SubscriptionSerializer(subscription)
            return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        """Create a new subscription"""
        serializer = SubscriptionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        plan_name = serializer.validated_data['plan']
        duration = serializer.validated_data['duration']
        grade = serializer.validated_data.get('grade')
        profile_ids = serializer.validated_data.get('profile_ids', [])
        
        # Validate grade for JUNIOR plan
        if plan_name == 'JUNIOR':
            if not grade:
                return Response(
                    {'grade': 'Grade is required for JUNIOR plan'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Check if user has a profile with this grade
            try:
                profile = request.user.profile
                if not profile.grade:
                    return Response(
                        {'error': 'Your profile does not have a grade set. Please update your profile first.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if profile.grade != grade:
                    return Response(
                        {'error': f'Your profile grade ({profile.get_grade_display()}) does not match the selected grade.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except UserProfile.DoesNotExist:
                return Response(
                    {'error': 'Profile not found. Please create a profile first.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Validate profiles for MASTER plan
        if plan_name == 'MASTER':
            if not profile_ids:
                return Response(
                    {'profile_ids': 'At least one profile ID is required for MASTER plan'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Verify all profiles belong to the user
            user_profiles = UserProfile.objects.filter(user=request.user, id__in=profile_ids)
            if user_profiles.count() != len(profile_ids):
                return Response(
                    {'error': 'One or more profile IDs do not belong to you or are invalid.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Verify all profiles have grades
            for profile in user_profiles:
                if not profile.grade:
                    return Response(
                        {'error': f'Profile "{profile.full_name}" does not have a grade set. Please update it first.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if profile.grade not in ['NURSERY', 'LKG', 'UKG']:
                    return Response(
                        {'error': f'Profile "{profile.full_name}" has an invalid grade for MASTER plan.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        
        # Validate profile limits
        validation = validate_profile_limits(request.user, plan_name)
        if not validation['can_create']:
            return Response(
                {'error': validation['message']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Create subscription
            subscription = create_subscription(
                user=request.user,
                plan_name=plan_name,
                duration=duration,
                grade=grade,
                profile_ids=profile_ids
            )
            
            serializer = SubscriptionSerializer(subscription)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Failed to create subscription: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubscriptionPriceView(APIView):
    """
    Calculate subscription price without creating a subscription.
    GET /api/auth/subscription/price/
    Query params: plan, duration, grade (for JUNIOR), profile_ids (for MASTER)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Calculate subscription price"""
        # Handle profile_ids from query params (can be multiple params or comma-separated)
        query_data = dict(request.query_params)
        profile_ids_param = request.query_params.getlist('profile_ids', [])
        
        # Convert to list of integers
        profile_ids = []
        if profile_ids_param:
            for param in profile_ids_param:
                # Handle comma-separated values
                if ',' in str(param):
                    profile_ids.extend([int(x.strip()) for x in str(param).split(',')])
                else:
                    try:
                        profile_ids.append(int(param))
                    except (ValueError, TypeError):
                        pass
        
        # Prepare data for serializer
        serializer_data = {
            'plan': query_data.get('plan', [None])[0] if isinstance(query_data.get('plan'), list) else query_data.get('plan'),
            'duration': query_data.get('duration', [None])[0] if isinstance(query_data.get('duration'), list) else query_data.get('duration'),
            'grade': query_data.get('grade', [None])[0] if isinstance(query_data.get('grade'), list) else query_data.get('grade'),
        }
        if profile_ids:
            serializer_data['profile_ids'] = profile_ids
        
        serializer = SubscriptionPriceSerializer(data=serializer_data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        plan_name = serializer.validated_data['plan']
        duration = serializer.validated_data['duration']
        grade = serializer.validated_data.get('grade')
        profile_ids = serializer.validated_data.get('profile_ids', [])
        
        # For MASTER plan, verify profiles belong to user
        if plan_name == 'MASTER' and profile_ids:
            user_profiles = UserProfile.objects.filter(user=request.user, id__in=profile_ids)
            if user_profiles.count() != len(profile_ids):
                return Response(
                    {'error': 'One or more profile IDs do not belong to you or are invalid.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            price_info = calculate_subscription_price(
                plan_name=plan_name,
                duration=duration,
                grade=grade,
                profile_ids=profile_ids
            )
            return Response(price_info, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Failed to calculate price: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== COURSE VIEWS ====================

class CourseListCreateView(APIView):
    """
    GET: List all courses
    POST: Create new course (Admin only)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        courses = Course.objects.filter(is_active=True)
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = CourseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CourseDetailView(APIView):
    """
    GET: View course details
    PUT: Update course (Admin only)
    DELETE: Delete course (Admin only)
    """
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return Course.objects.get(pk=pk, is_active=True)
        except Course.DoesNotExist:
            return None
    
    def get(self, request, pk):
        course = self.get_object(pk)
        if not course:
            return Response(
                {"error": "Course not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = CourseSerializer(course)
        return Response(serializer.data)
    
    def put(self, request, pk):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        course = self.get_object(pk)
        if not course:
            return Response(
                {"error": "Course not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CourseSerializer(course, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        course = self.get_object(pk)
        if not course:
            return Response(
                {"error": "Course not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        course.is_active = False  # Soft delete
        course.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ==================== SYLLABUS VIEWS ====================

class SyllabusListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        syllabi = Syllabus.objects.filter(is_active=True)
        serializer = SyllabusSerializer(syllabi, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = SyllabusSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SyllabusDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return Syllabus.objects.get(pk=pk, is_active=True)
        except Syllabus.DoesNotExist:
            return None
    
    def get(self, request, pk):
        syllabus = self.get_object(pk)
        if not syllabus:
            return Response(
                {"error": "Syllabus not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = SyllabusSerializer(syllabus)
        return Response(serializer.data)
    
    def put(self, request, pk):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        syllabus = self.get_object(pk)
        if not syllabus:
            return Response(
                {"error": "Syllabus not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = SyllabusSerializer(syllabus, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        syllabus = self.get_object(pk)
        if not syllabus:
            return Response(
                {"error": "Syllabus not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        syllabus.is_active = False
        syllabus.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ==================== SUBJECT VIEWS ====================

class SubjectListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        subjects = Subject.objects.filter(is_active=True)
        serializer = SubjectSerializer(subjects, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = SubjectSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SubjectDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return Subject.objects.get(pk=pk, is_active=True)
        except Subject.DoesNotExist:
            return None
    
    def get(self, request, pk):
        subject = self.get_object(pk)
        if not subject:
            return Response(
                {"error": "Subject not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = SubjectSerializer(subject)
        return Response(serializer.data)
    
    def put(self, request, pk):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        subject = self.get_object(pk)
        if not subject:
            return Response(
                {"error": "Subject not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = SubjectSerializer(subject, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        subject = self.get_object(pk)
        if not subject:
            return Response(
                {"error": "Subject not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        subject.is_active = False
        subject.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ==================== CHAPTER VIEWS ====================

class ChapterListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        chapters = Chapter.objects.filter(is_active=True)
        serializer = ChapterSerializer(chapters, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ChapterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChapterDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return Chapter.objects.get(pk=pk, is_active=True)
        except Chapter.DoesNotExist:
            return None
    
    def get(self, request, pk):
        chapter = self.get_object(pk)
        if not chapter:
            return Response(
                {"error": "Chapter not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ChapterSerializer(chapter)
        return Response(serializer.data)
    
    def put(self, request, pk):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        chapter = self.get_object(pk)
        if not chapter:
            return Response(
                {"error": "Chapter not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ChapterSerializer(chapter, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        chapter = self.get_object(pk)
        if not chapter:
            return Response(
                {"error": "Chapter not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        chapter.is_active = False
        chapter.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ==================== TOPIC VIEWS ====================

class TopicListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        topics = Topic.objects.filter(is_active=True)
        serializer = TopicSerializer(topics, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = TopicSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TopicDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return Topic.objects.get(pk=pk, is_active=True)
        except Topic.DoesNotExist:
            return None
    
    def get(self, request, pk):
        topic = self.get_object(pk)
        if not topic:
            return Response(
                {"error": "Topic not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = TopicSerializer(topic)
        return Response(serializer.data)
    
    def put(self, request, pk):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        topic = self.get_object(pk)
        if not topic:
            return Response(
                {"error": "Topic not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = TopicSerializer(topic, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        if not request.user.is_staff:
            return Response(
                {"error": "Admin access required"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        topic = self.get_object(pk)
        if not topic:
            return Response(
                {"error": "Topic not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        topic.is_active = False
        topic.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

class AdminProcessTopicBatchView(APIView):
    """
    Admin manually triggers YouTube search for topics
    Runs processing function in background thread
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Check admin permission
        # if not request.user.is_staff:
        #     return Response(
        #         {"error": "Admin access required"}, 
        #         status=status.HTTP_403_FORBIDDEN
        #     )
        
        # Import processing function
        from .cron import process_topic_batch
        
        # Run in background thread
        thread = threading.Thread(target=process_topic_batch)
        thread.daemon = True
        thread.start()
        
        # Return immediately
        return Response({
            "message": "Topic batch processing started in background"
        }, status=status.HTTP_202_ACCEPTED)



class AdminTaskListCreateView(APIView):
    """Admin: List and create tasks"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # if not request.user.is_staff:
        #     return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)
        
        grade = request.query_params.get('grade')
        tasks = Task.objects.filter(is_active=True)
        
        if grade:
            tasks = tasks.filter(grade=grade)
        
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # if not request.user.is_staff:
        #     return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = TaskSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class AdminTaskDetailView(APIView):
    """Admin: Get, update, delete task"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return Task.objects.get(pk=pk, is_active=True)
        except Task.DoesNotExist:
            return None
    
    def get(self, request, pk):
        # if not request.user.is_staff:
        #     return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)
        
        task = self.get_object(pk)
        if not task:
            return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = TaskSerializer(task)
        return Response(serializer.data)
    
    def put(self, request, pk):
        # if not request.user.is_staff:
        #     return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)
        
        task = self.get_object(pk)
        if not task:
            return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = TaskSerializer(task, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        if not request.user.is_staff:
            return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)
        
        task = self.get_object(pk)
        if not task:
            return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)
        
        task.is_active = False
        task.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

class AdminAddVideoItemView(APIView):
    """Admin: Add video item to task"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, task_id):
        # if not request.user.is_staff:
        #     return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            task = Task.objects.get(pk=task_id, is_active=True)
        except Task.DoesNotExist:
            return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AddVideoItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Check video exists and is approved
        # Task, TaskItem, TaskVideo are already imported at top level
        # VideoResult is also imported at top level
        
        if serializer.is_valid():
            try:
                task = Task.objects.get(pk=task_id)
                video = VideoResult.objects.get(
                    pk=serializer.validated_data['video_id'],
                    approval_status='APPROVED'
                )
                
                # Create TaskItem
                task_item = TaskItem.objects.create(
                    task=task,
                    item_type='VIDEO',
                    title=serializer.validated_data['title'],
                    day_number=serializer.validated_data['day_number'],
                    order=serializer.validated_data.get('order', 0)
                )
                
                # Create TaskVideo
                task_video = TaskVideo.objects.create(
                    task_item=task_item,
                    video=video
                )
                
                return Response(
                    TaskItemSerializer(task_item).data,
                    status=status.HTTP_201_CREATED
                )
            except Task.DoesNotExist:
                return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)
            except VideoResult.DoesNotExist:
                return Response({"error": "Approved video not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
class AdminAddQuizItemView(APIView):
    """Admin: Add quiz item to task"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, task_id):
        try:
            task = Task.objects.get(pk=task_id, is_active=True)
        except Task.DoesNotExist:
            return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AddQuizItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Create task item
        task_item = TaskItem.objects.create(
            task=task,
            item_type='QUIZ',
            title=serializer.validated_data['title'],
            day_number=serializer.validated_data['day_number'],
            order=serializer.validated_data.get('order', 0)
        )
        
        # Create quiz data
        TaskQuiz.objects.create(
            task_item=task_item,
            quiz_type=serializer.validated_data.get('quiz_type', 'QUESTION_OPTIONS'),
            questions=serializer.validated_data['questions'],
            passing_score=serializer.validated_data.get('passing_score', 60),
            time_limit=serializer.validated_data.get('time_limit'),
            shuffle_questions=serializer.validated_data.get('shuffle_questions', True)
        )
        
        return Response(TaskItemSerializer(task_item).data, status=status.HTTP_201_CREATED)

class AdminEditQuizItemView(APIView):
    """Admin: Edit existing quiz item"""
    permission_classes = [IsAuthenticated]
    
    def put(self, request, task_item_id):
        """Update quiz item and quiz data"""
        try:
            task_item = TaskItem.objects.get(pk=task_item_id, item_type='QUIZ', is_active=True)
        except TaskItem.DoesNotExist:
            return Response({"error": "Quiz item not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AddQuizItemSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Update TaskItem fields
        if 'title' in serializer.validated_data:
            task_item.title = serializer.validated_data['title']
        if 'description' in serializer.validated_data:
            task_item.description = serializer.validated_data['description']
        if 'day_number' in serializer.validated_data:
            task_item.day_number = serializer.validated_data['day_number']
        if 'order' in serializer.validated_data:
            task_item.order = serializer.validated_data['order']
        task_item.save()
        
        # Update TaskQuiz fields
        try:
            quiz = task_item.quiz_data
            if 'quiz_type' in serializer.validated_data:
                quiz.quiz_type = serializer.validated_data['quiz_type']
            if 'questions' in serializer.validated_data:
                quiz.questions = serializer.validated_data['questions']
            if 'passing_score' in serializer.validated_data:
                quiz.passing_score = serializer.validated_data['passing_score']
            if 'time_limit' in serializer.validated_data:
                quiz.time_limit = serializer.validated_data['time_limit']
            if 'shuffle_questions' in serializer.validated_data:
                quiz.shuffle_questions = serializer.validated_data['shuffle_questions']
            quiz.save()
        except TaskQuiz.DoesNotExist:
            return Response({"error": "Quiz data not found"}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(TaskItemSerializer(task_item).data, status=status.HTTP_200_OK)
    
    def delete(self, request, task_item_id):
        """Delete quiz item (soft delete)"""
        try:
            task_item = TaskItem.objects.get(pk=task_item_id, item_type='QUIZ', is_active=True)
        except TaskItem.DoesNotExist:
            return Response({"error": "Quiz item not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Soft delete
        task_item.is_active = False
        task_item.save()
        
        return Response({"message": "Quiz item deleted successfully"}, status=status.HTTP_204_NO_CONTENT)



class AdminEditVideoItemView(APIView):
    """Admin: Edit existing video item"""
    permission_classes = [IsAuthenticated]
    
    def put(self, request, task_item_id):
        """Update video item"""
        try:
            task_item = TaskItem.objects.get(pk=task_item_id, item_type='VIDEO', is_active=True)
        except TaskItem.DoesNotExist:
            return Response({"error": "Video item not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AddVideoItemSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Update TaskItem fields
        if 'title' in serializer.validated_data:
            task_item.title = serializer.validated_data['title']
        if 'day_number' in serializer.validated_data:
            task_item.day_number = serializer.validated_data['day_number']
        if 'order' in serializer.validated_data:
            task_item.order = serializer.validated_data['order']
        task_item.save()
        
        # Update TaskVideo if video_id is provided
        if 'video_id' in serializer.validated_data:
            try:
                video = VideoResult.objects.get(
                    pk=serializer.validated_data['video_id'],
                    approval_status='APPROVED'
                )
                task_video = task_item.video_data
                task_video.video = video
                task_video.save()
            except VideoResult.DoesNotExist:
                return Response({"error": "Approved video not found"}, status=status.HTTP_404_NOT_FOUND)
            except TaskVideo.DoesNotExist:
                return Response({"error": "Video data not found"}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(TaskItemSerializer(task_item).data, status=status.HTTP_200_OK)
    
    def delete(self, request, task_item_id):
        """Delete video item (soft delete)"""
        try:
            task_item = TaskItem.objects.get(pk=task_item_id, item_type='VIDEO', is_active=True)
        except TaskItem.DoesNotExist:
            return Response({"error": "Video item not found"}, status=status.HTTP_404_NOT_FOUND)
        
        task_item.is_active = False
        task_item.save()
        
        return Response({"message": "Video item deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class AdminEditGameItemView(APIView):
    """Admin: Edit existing game item"""
    permission_classes = [IsAuthenticated]
    
    def put(self, request, task_item_id):
        """Update game item"""
        try:
            task_item = TaskItem.objects.get(pk=task_item_id, item_type='GAME', is_active=True)
        except TaskItem.DoesNotExist:
            return Response({"error": "Game item not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AddGameItemSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Update TaskItem fields
        if 'title' in serializer.validated_data:
            task_item.title = serializer.validated_data['title']
        if 'day_number' in serializer.validated_data:
            task_item.day_number = serializer.validated_data['day_number']
        if 'order' in serializer.validated_data:
            task_item.order = serializer.validated_data['order']
        task_item.save()
        
        # Update TaskGame fields
        try:
            game = task_item.game_data
            if 'game_url' in serializer.validated_data:
                game.game_url = serializer.validated_data['game_url']
            if 'difficulty' in serializer.validated_data:
                game.difficulty = serializer.validated_data['difficulty']
            if 'instructions' in serializer.validated_data:
                game.instructions = serializer.validated_data['instructions']
            game.save()
        except TaskGame.DoesNotExist:
            return Response({"error": "Game data not found"}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(TaskItemSerializer(task_item).data, status=status.HTTP_200_OK)
    
    def delete(self, request, task_item_id):
        """Delete game item (soft delete)"""
        try:
            task_item = TaskItem.objects.get(pk=task_item_id, item_type='GAME', is_active=True)
        except TaskItem.DoesNotExist:
            return Response({"error": "Game item not found"}, status=status.HTTP_404_NOT_FOUND)
        
        task_item.is_active = False
        task_item.save()
        
        return Response({"message": "Game item deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class AdminEditActivityItemView(APIView):
    """Admin: Edit existing activity item"""
    permission_classes = [IsAuthenticated]
    
    def put(self, request, task_item_id):
        """Update activity item"""
        try:
            task_item = TaskItem.objects.get(pk=task_item_id, item_type='ACTIVITY', is_active=True)
        except TaskItem.DoesNotExist:
            return Response({"error": "Activity item not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AddActivityItemSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Update TaskItem fields
        if 'title' in serializer.validated_data:
            task_item.title = serializer.validated_data['title']
        if 'day_number' in serializer.validated_data:
            task_item.day_number = serializer.validated_data['day_number']
        if 'order' in serializer.validated_data:
            task_item.order = serializer.validated_data['order']
        task_item.save()
        
        # Update TaskActivity fields
        try:
            activity = task_item.activity_data
            if 'instructions' in serializer.validated_data:
                activity.instructions = serializer.validated_data['instructions']
            if 'materials_needed' in serializer.validated_data:
                activity.materials_needed = serializer.validated_data['materials_needed']
            if 'estimated_time' in serializer.validated_data:
                activity.estimated_time = serializer.validated_data['estimated_time']
            activity.save()
        except TaskActivity.DoesNotExist:
            return Response({"error": "Activity data not found"}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(TaskItemSerializer(task_item).data, status=status.HTTP_200_OK)
    
    def delete(self, request, task_item_id):
        """Delete activity item (soft delete)"""
        try:
            task_item = TaskItem.objects.get(pk=task_item_id, item_type='ACTIVITY', is_active=True)
        except TaskItem.DoesNotExist:
            return Response({"error": "Activity item not found"}, status=status.HTTP_404_NOT_FOUND)
        
        task_item.is_active = False
        task_item.save()
        
        return Response({"message": "Activity item deleted successfully"}, status=status.HTTP_204_NO_CONTENT)



class AdminAddGameItemView(APIView):
    """Admin: Add game item to task"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, task_id):
        # if not request.user.is_staff:
        #     return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            task = Task.objects.get(pk=task_id, is_active=True)
        except Task.DoesNotExist:
            return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AddGameItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Create task item
        task_item = TaskItem.objects.create(
            task=task,
            item_type='GAME',
            title=serializer.validated_data['title'],
            day_number=serializer.validated_data['day_number'],
            order=serializer.validated_data.get('order', 0)
        )
        
        # Create game data
        TaskGame.objects.create(
            task_item=task_item,
            game_url=serializer.validated_data['game_url'],
            difficulty=serializer.validated_data.get('difficulty', 'EASY')
        )
        
        return Response(TaskItemSerializer(task_item).data, status=status.HTTP_201_CREATED)
class AdminAddActivityItemView(APIView):
    """Admin: Add activity item to task"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, task_id):
        try:
            task = Task.objects.get(pk=task_id, is_active=True)
        except Task.DoesNotExist:
            return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AddActivityItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Create task item
        task_item = TaskItem.objects.create(
            task=task,
            item_type='ACTIVITY',
            title=serializer.validated_data['title'],
            day_number=serializer.validated_data['day_number'],
            order=serializer.validated_data.get('order', 0)
        )
        
        # Create activity data
        TaskActivity.objects.create(
            task_item=task_item,
            instructions=serializer.validated_data['instructions'],
            materials_needed=serializer.validated_data.get('materials_needed', ''),
            estimated_time=serializer.validated_data['estimated_time']
        )
        
        return Response(TaskItemSerializer(task_item).data, status=status.HTTP_201_CREATED)
class AdminApprovedVideosListView(APIView):
    """Admin: List approved videos for selection"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # if not request.user.is_staff:
        #     return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)
        
        # VideoResult already imported at top level
        from .serializers import VideoResultSerializer
        
        videos = VideoResult.objects.filter(approval_status='APPROVED')
        
        # Filter by grade
        grade = request.query_params.get('grade')
        if grade:
            videos = videos.filter(topic__chapter__subject__syllabus__course__grade=grade)
        
        # Search by title
        search = request.query_params.get('search')
        if search:
            videos = videos.filter(title__icontains=search)
        
        videos = videos.order_by('-id')[:50]  # Limit to 50
        serializer = VideoResultSerializer(videos, many=True)
        return Response(serializer.data)


# ==================== QUIZ ANSWER SUBMISSION ====================

class SubmitQuizAnswerView(APIView):
    """
    Submit and check quiz answers
    POST /api/auth/submit-quiz-answer/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from .serializers import QuizAnswerSerializer
        
        serializer = QuizAnswerSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        task_item_id = serializer.validated_data['task_item_id']
        user_answers = serializer.validated_data['user_answers']
        time_taken = serializer.validated_data.get('time_taken')
        
        # Get quiz
        try:
            task_item = TaskItem.objects.get(pk=task_item_id, item_type='QUIZ', is_active=True)
            quiz = task_item.quiz_data
        except TaskItem.DoesNotExist:
            return Response({"error": "Quiz not found"}, status=status.HTTP_404_NOT_FOUND)
        except TaskQuiz.DoesNotExist:
            return Response({"error": "Quiz data not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Validate based on quiz type
        if quiz.quiz_type == 'MATCH_MAKING':
            result = self.validate_match_making(quiz, user_answers)
        else:  # QUESTION_OPTIONS
            result = self.validate_question_options(quiz, user_answers)
        
        # Add time_taken to result
        if time_taken:
            result['time_taken'] = time_taken
        
        return Response(result)
    
    def validate_question_options(self, quiz, user_answers):
        """Validate question-options quiz answers"""
        questions = quiz.questions
        total_questions = len(questions)
        correct_count = 0
        
        detailed_feedback = []
        
        # user_answers format: [{"question_id": 1, "selected_answer": "b"}, ...]
        user_answers_dict = {ans.get('question_id'): ans.get('selected_answer') for ans in user_answers}
        
        for q in questions:
            question_id = q.get('id')
            correct_answer = q.get('correct_answer')
            user_answer = user_answers_dict.get(question_id)
            
            is_correct = user_answer == correct_answer
            if is_correct:
                correct_count += 1
            
            # Find selected option text
            selected_option = next((opt for opt in q.get('options', []) if opt.get('id') == user_answer), None)
            correct_option = next((opt for opt in q.get('options', []) if opt.get('id') == correct_answer), None)
            
            detailed_feedback.append({
                'question_id': question_id,
                'question': q.get('question'),
                'user_answer': selected_option.get('text') if selected_option else None,
                'correct_answer': correct_option.get('text') if correct_option else None,
                'is_correct': is_correct,
                'explanation': q.get('explanation')
            })
        
        # Calculate percentage
        percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0
        passed = percentage >= quiz.passing_score
        
        return {
            'passed': passed,
            'score': round(percentage, 2),
            'correct_count': correct_count,
            'total_count': total_questions,
            'passing_score': quiz.passing_score,
            'detailed_feedback': detailed_feedback,
            'message': f"You got {correct_count} out of {total_questions} correct! {'Well done!' if passed else 'Keep practicing!'}"
        }
    
    def validate_match_making(self, quiz, user_matches):
        """Validate match-making quiz answers"""
        question = quiz.questions[0]  # Match-making typically has one question with multiple pairs
        correct_matches = question.get('correct_matches', [])
        pairs = question.get('pairs', [])
        
        # Convert to dict for easy comparison
        # user_matches format: [{"left_id": "l1", "right_id": "r2"}, ...]
        correct_dict = {cm['left_id']: cm['right_id'] for cm in correct_matches}
        user_dict = {um['left_id']: um['right_id'] for um in user_matches}
        
        # Count correct matches
        total_pairs = len(correct_matches)
        correct_count = 0
        
        detailed_feedback = []
        
        for pair in pairs:
            left_id = pair['left']['id']
            correct_right_id = correct_dict.get(left_id)
            user_right_id = user_dict.get(left_id)
            is_correct = user_right_id == correct_right_id
            
            if is_correct:
                correct_count += 1
            
            # Get text for feedback
            correct_right = next((p['right'] for p in pairs if p['right']['id'] == correct_right_id), None)
            user_right = next((p['right'] for p in pairs if p['right']['id'] == user_right_id), None) if user_right_id else None
            
            detailed_feedback.append({
                'left': pair['left'].get('text') or f"Item {left_id}",
                'user_answer': user_right.get('text') if user_right else 'Not matched',
                'correct_answer': correct_right.get('text') if correct_right else 'Unknown',
                'is_correct': is_correct
            })
        
        # Calculate percentage
        percentage = (correct_count / total_pairs * 100) if total_pairs > 0 else 0
        passed = percentage >= quiz.passing_score
        
        return {
            'passed': passed,
            'score': round(percentage, 2),
            'correct_count': correct_count,
            'total_count': total_pairs,
            'passing_score': quiz.passing_score,
            'detailed_feedback': detailed_feedback,
            'message': f"You matched {correct_count} out of {total_pairs} correctly! {'Excellent!' if passed else 'Try again!'}"
        }


# ==================== VIDEO MANAGEMENT VIEWS ====================

class VideoListView(APIView):
    """
    List all videos with optional filtering
    GET /api/auth/videos/?approval_status=PENDING&topic=1
    """
    def get(self, request):
        from .serializers import VideoResultSerializer
        
        # Get all videos
        videos = VideoResult.objects.all()
        
        # Filter by approval_status if provided
        approval_status = request.query_params.get('approval_status')
        if approval_status:
            videos = videos.filter(approval_status=approval_status)
        
        # Filter by topic if provided
        topic_id = request.query_params.get('topic')
        if topic_id:
            videos = videos.filter(topic_id=topic_id)
        
        # Filter by tag if provided  
        tag_id = request.query_params.get('tag')
        if tag_id:
            videos = videos.filter(tag_id=tag_id)
        
        # Order by created date (newest first)
        videos = videos.order_by('-created_at')
        
        serializer = VideoResultSerializer(videos, many=True)
        return Response(serializer.data)


class VideoDetailView(APIView):
    """
    GET: View single video details
    PUT: Update video (approval_status, topic)
    DELETE: Delete video
    """
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        """Helper method to get video by ID"""
        try:
            return VideoResult.objects.get(pk=pk)
        except VideoResult.DoesNotExist:
            return None
    
    def get(self, request, pk):
        """Get video details"""
        from .serializers import VideoResultSerializer
        
        video = self.get_object(pk)
        if not video:
            return Response(
                {"error": "Video not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = VideoResultSerializer(video)
        return Response(serializer.data)
    
    def put(self, request, pk):
        """Update video (approval_status, topic)"""
        from .serializers import VideoResultSerializer
        
        video = self.get_object(pk)
        if not video:
            return Response(
                {"error": "Video not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = VideoResultSerializer(video, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """Delete video"""
        video = self.get_object(pk)
        if not video:
            return Response(
                {"error": "Video not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        video.delete()
        return Response(
            {"message": "Video deleted successfully"}, 
            status=status.HTTP_204_NO_CONTENT
        )


class VideoApproveView(APIView):
    """
    Quick approve a video
    POST /api/auth/videos/{id}/approve/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        from .serializers import VideoResultSerializer
        
        try:
            video = VideoResult.objects.get(pk=pk)
        except VideoResult.DoesNotExist:
            return Response(
                {"error": "Video not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update approval status
        video.approval_status = 'APPROVED'
        video.save()
        
        serializer = VideoResultSerializer(video)
        return Response({
            "message": "Video approved successfully",
            "video": serializer.data
        })


class VideoDisapproveView(APIView):
    """
    Quick disapprove a video
    POST /api/auth/videos/{id}/disapprove/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        from .serializers import VideoResultSerializer
        
        try:
            video = VideoResult.objects.get(pk=pk)
        except VideoResult.DoesNotExist:
            return Response(
                {"error": "Video not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update approval status
        video.approval_status = 'DISAPPROVED'
        video.save()
        
        serializer = VideoResultSerializer(video)
        return Response({
            "message": "Video disapproved successfully",
            "video": serializer.data
        })