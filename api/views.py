
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