from django.utils import timezone
from .models import Topic
from api.models import VideoResult
from api.youtube_client import get_youtube_videos
import logging

logger = logging.getLogger(__name__)


def process_topic_batch():
    """
    Process next 80 pending topics
    Can be triggered manually from admin endpoint
    """
    logger.info("Starting topic batch processing...")
    
    # Get next 80 pending topics
    topics_to_search = Topic.objects.filter(
        search_status='PENDING',
        is_active=True
    ).order_by('id')[:80]
    
    if not topics_to_search.exists():
        logger.info("No pending topics to search")
        return "No pending topics"
    
    # Mark as PROCESSING
    topic_ids = [t.id for t in topics_to_search]
    Topic.objects.filter(id__in=topic_ids).update(search_status='PROCESSING')
    
    logger.info(f"Processing {len(topic_ids)} topics...")
    processed_count = 0
    videos_created = 0
    
    # Process each topic
    for topic_id in topic_ids:
        try:
            topic = Topic.objects.get(id=topic_id)
            
            # Build comprehensive search query
            # Format: "Topic name Chapter name Subject Grade"
            # Example: "Counting 1-10 Numbers Mathematics LKG"
            chapter = topic.chapter
            subject = chapter.subject
            syllabus = subject.syllabus
            course = syllabus.course
            
            search_query = f"{topic.title} {chapter.title} {subject.name} {course.grade}"
            logger.info(f"Searching YouTube for: {search_query}")
            
            # Search YouTube using comprehensive query
            video_items = get_youtube_videos(search_query, max_results=10)
            
            if not video_items:
                topic.search_status = 'COMPLETED'
                topic.last_searched_at = timezone.now()
                topic.save()
                processed_count += 1
                continue
            
            # Save videos
            for item in video_items:
                video_id = item.get('video_id')
                if not video_id:
                    continue
                
                # Skip if exists
                if VideoResult.objects.filter(topic=topic, video_id=video_id).exists():
                    continue
                
                VideoResult.objects.create(
                    topic=topic,
                    video_id=video_id,
                    approval_status='PENDING',
                    title=item.get('title'),
                    description=item.get('full_description'),
                    url=item.get('url'),
                    thumbnail_url=item.get('thumbnail_url'),
                    channel_title=item.get('channel_title'),
                    published_at=item.get('published_at'),
                    duration=item.get('duration'),
                    view_count=item.get('view_count'),
                    like_count=item.get('like_count'),
                    comment_count=item.get('comment_count'),
                    tags_from_video=item.get('tags'),
                    category_id=item.get('category_id')
                )
                videos_created += 1
            
            # Mark as COMPLETED
            topic.search_status = 'COMPLETED'
            topic.last_searched_at = timezone.now()
            topic.save()
            processed_count += 1
            
        except Exception as e:
            logger.error(f"Failed to process topic {topic_id}: {e}")
            try:
                topic.search_status = 'FAILED'
                topic.save()
            except:
                pass
    
    result = f"Processed {processed_count} topics, created {videos_created} videos"
    logger.info(result)
    return result