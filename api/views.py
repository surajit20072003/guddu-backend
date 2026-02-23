
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAdminUser  # <-- Use IsAdminUser

# Import our models, serializers, and tasks
from .models import SearchRequest
from .serializers import SearchUploadSerializer
from .tasks import extract_tags_from_request, process_tag_batch

class AdminUploadView(APIView):
    """
    Endpoint 1: Admin uploads a file.
    This creates the SearchRequest and starts the *tag extraction* task.
    """
    parser_classes = (MultiPartParser, FormParser)
    #permission_classes = [IsAdminUser] # Only admins can access

    def post(self, request, *args, **kwargs):
        
        # 1. Validate the file upload
        upload_serializer = SearchUploadSerializer(data=request.data)
        if not upload_serializer.is_valid():
            return Response(upload_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = upload_serializer.validated_data
        
        # 2. Save the initial SearchRequest object
        try:
            search_request = SearchRequest.objects.create(
                uploaded_file=validated_data.get('uploaded_file'),
                tags_from_user=validated_data.get('tags_from_user', ""),
                class_level=validated_data.get('class_level', ""),
                year=validated_data.get('year'),
                status='PENDING' # Status is PENDING (tag extraction)
            )
        except Exception as e:
            return Response({"error": f"Failed to save request: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 3. Call the background task
        # We give it the ID, and it will do the rest.
        extract_tags_from_request.delay(search_request.id)

        # 4. Return an immediate response
        return Response(
            {"message": f"File received. Tag extraction for Request ID {search_request.id} has started in the background."},
            status=status.HTTP_202_ACCEPTED
        )

class AdminStartBatchView(APIView):
    """
    Endpoint 2: Admin clicks the "Start Batch" button.
    This starts the *YouTube search* task.
    """
    #permission_classes = [IsAuthe] # Only admins can access

    def post(self, request, *args, **kwargs):
        
        # 1. Call the background task
        process_tag_batch.delay()
        
        # 2. Return an immediate response
        return Response(
            {"message": "Batch processing of 80 tags has started in the background."},
            status=status.HTTP_202_ACCEPTED
        )


class VideoListView(APIView):
    """
    List all videos with optional filtering
    GET /api/videos/?approval_status=PENDING&topic=1
    """
    def get(self, request):
        from authentication.models import VideoResult
        from authentication.serializers import VideoResultSerializer
        
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
        videos = videos.order_by('-id')
        
        serializer = VideoResultSerializer(videos, many=True)
        return Response(serializer.data)


class VideoDetailView(APIView):
    """
    GET: View single video details
    PUT: Update video (approval_status, topic)
    DELETE: Delete video
    """
    # permission_classes = [IsAdminUser]  # Uncomment for production
    
    def get_object(self, pk):
        """Helper method to get video by ID"""
        from authentication.models import VideoResult
        try:
            return VideoResult.objects.get(pk=pk)
        except VideoResult.DoesNotExist:
            return None
    
    def get(self, request, pk):
        """Get video details"""
        from authentication.serializers import VideoResultSerializer
        
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
        from authentication.serializers import VideoResultSerializer
        
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
    POST /api/videos/{id}/approve/
    """
    # permission_classes = [IsAdminUser]  # Uncomment for production
    
    def post(self, request, pk):
        from authentication.models import VideoResult
        from authentication.serializers import VideoResultSerializer
        
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
    POST /api/videos/{id}/disapprove/
    """
    # permission_classes = [IsAdminUser]  # Uncomment for production
    
    def post(self, request, pk):
        from authentication.models import VideoResult
        from authentication.serializers import VideoResultSerializer
        
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