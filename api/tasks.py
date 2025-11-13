# api/tasks.py
from celery import shared_task
from django.utils import timezone
from .models import SearchRequest, KeywordTag, VideoResult
from .parsers import get_keywords_from_file, extract_keywords_from_text
from .youtube_client import get_youtube_videos

@shared_task
def extract_tags_from_request(request_id):
    """
    Task 1: Called by the admin upload.
    Parses the file from a SearchRequest and creates PENDING KeywordTags.
    """
    try:
        search_request = SearchRequest.objects.get(id=request_id)
    except SearchRequest.DoesNotExist:
        print(f"SearchRequest {request_id} not found.")
        return

    all_raw_tags = []
    
    # 1. Get keywords from user tags
    if search_request.tags_from_user:
        all_raw_tags.extend([tag.strip() for tag in search_request.tags_from_user.split(',')])

    # 2. Get keywords from file
    if search_request.uploaded_file:
        file_text = get_keywords_from_file(search_request.uploaded_file.path)
        if file_text:
            file_keywords = extract_keywords_from_text(file_text)
            all_raw_tags.extend(file_keywords)
    
    if not all_raw_tags:
        search_request.status = 'FAILED'
        search_request.save()
        print(f"No keywords found for SearchRequest {request_id}.")
        return

    # 3. Create the final class suffix
    class_level_input = search_request.class_level or ""
    class_suffix = ""
    if class_level_input:
        if class_level_input.isdigit():
            class_suffix = f" for class {class_level_input}"
        else:
            class_suffix = f" for {class_level_input}"

    # 4. Create the KeywordTag objects
    tags_created = 0
    for tag_text in list(set(all_raw_tags)):
        if not tag_text:
            continue
        
        final_tag_text = f"{tag_text}{class_suffix}"
        
        tag_obj, created = KeywordTag.objects.get_or_create(
            tag_text=final_tag_text
        )
        
        # --- THIS IS THE FIX ---
        # Link this tag to the request that created it.
        tag_obj.search_requests.add(search_request)
        # --- END OF FIX ---
        
        if created:
            tags_created += 1
            
    # 5. Mark the SearchRequest as completed
    search_request.status = 'COMPLETED'
    search_request.save()
    
    return f"Processed SearchRequest {request_id}. Created {tags_created} new tags."


@shared_task
def process_tag_batch():
    """
    Task 2: Called by the admin "Start Batch" button.
    (This function is correct, no changes needed)
    """
    # 1. Get the next 80 "To-Do" items
    tags_to_search = KeywordTag.objects.filter(status='PENDING').order_by('id')[:80]
    
    if not tags_to_search.exists():
        print("No pending tags to search.")
        return "No pending tags."

    # 2. Mark them all as 'PROCESSING' first
    tag_ids = [tag.id for tag in tags_to_search]
    KeywordTag.objects.filter(id__in=tag_ids).update(status='PROCESSING')
    
    print(f"Starting batch process for {len(tag_ids)} tags...")
    processed_count = 0

    # 3. Now, loop through and process them
    for tag_id in tag_ids:
        try:
            tag = KeywordTag.objects.get(id=tag_id)
            
            # 4. Call YouTube API
            video_items = get_youtube_videos(tag.tag_text, max_results=10)
            
            # 5. Save results
            for item in video_items:
                video_id = item.get('video_id')
                if not video_id:
                    continue
                
                VideoResult.objects.update_or_create(
                    tag=tag,
                    video_id=video_id,
                    defaults={
                        'approval_status': 'PENDING',
                        'title': item.get('title'),
                        'description': item.get('full_description'),
                        'url': item.get('url'),
                        'thumbnail_url': item.get('thumbnail_url'),
                        'channel_title': item.get('channel_title'),
                        'published_at': item.get('published_at'),
                        'duration': item.get('duration'),
                        'view_count': item.get('view_count'),
                        'like_count': item.get('like_count'),
                        'comment_count': item.get('comment_count'),
                        'tags_from_video': item.get('tags'),
                        'category_id': item.get('category_id')
                    }
                )

            # 6. Mark as COMPLETED
            tag.status = 'COMPLETED'
            tag.last_searched_at = timezone.now()
            tag.save()
            processed_count += 1

        except Exception as e:
            print(f"Failed to process tag: {tag.tag_text}. Error: {e}")
            try:
                tag.status = 'FAILED'
                tag.save()
            except: pass # Ignore errors if tag object is gone

    return f"Batch complete. Processed {processed_count} tags."