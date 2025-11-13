
from googleapiclient.discovery import build
from django.conf import settings
from dateutil import parser # Used to convert YouTube's date string

def get_youtube_videos(query, max_results=40):
    """
    Calls the YouTube API v3 to search for videos and get their full details.
    """
    
    # Get API Key from settings.py
    api_key = getattr(settings, 'YOUTUBE_API_KEY', None)
    if not api_key:
        print("ERROR: YOUTUBE_API_KEY is not set in settings.py")
        return []

    try:
        youtube = build('youtube', 'v3', developerKey=api_key)

        # --- Step 1: Search for videos ---
        search_request = youtube.search().list(
            part='snippet',
            q=query,
            type='video',
            maxResults=max_results
        )
        search_response = search_request.execute()

        video_ids = []
        basic_video_data = {} # Store data from search here
        
        for item in search_response.get('items', []):
            video_id = item['id']['videoId']
            video_ids.append(video_id)
            
            snippet = item.get('snippet', {})
            basic_video_data[video_id] = {
                'video_id': video_id,
                'title': snippet.get('title'),
                'description_snippet': snippet.get('description'),
                'url': f'https://www.youtube.com/watch?v={video_id}',
                'thumbnail_url': snippet.get('thumbnails', {}).get('high', {}).get('url'),
                'channel_title': snippet.get('channelTitle'),
                'published_at_str': snippet.get('publishedAt') # Get the raw date string
            }

        if not video_ids:
            return [] # No videos found

        # --- Step 2: Get full details for all found videos at once ---
        video_details_request = youtube.videos().list(
            part='snippet,contentDetails,statistics', # Ask for all the fields
            id=','.join(video_ids) # Pass all IDs at once (this is 1 API unit)
        )
        video_details_response = video_details_request.execute()

        final_video_list = []
        for item in video_details_response.get('items', []):
            video_id = item['id']
            
            # Get the basic data from our search
            video_data = basic_video_data.get(video_id, {})
            
            # Now add more details
            snippet = item.get('snippet', {})
            video_data['full_description'] = snippet.get('description')
            video_data['tags'] = ",".join(snippet.get('tags', [])) # Join tags into a string
            video_data['category_id'] = snippet.get('categoryId')
            
            # Parse the string date into a real datetime object
            if 'published_at_str' in video_data and video_data['published_at_str']:
                 video_data['published_at'] = parser.isoparse(video_data['published_at_str'])

            content_details = item.get('contentDetails', {})
            video_data['duration'] = content_details.get('duration')

            statistics = item.get('statistics', {})
            video_data['view_count'] = int(statistics.get('viewCount', 0))
            video_data['like_count'] = int(statistics.get('likeCount', 0))
            video_data['comment_count'] = int(statistics.get('commentCount', 0))

            final_video_list.append(video_data)

        return final_video_list

    except Exception as e:
        print(f"Error calling YouTube API: {e}")
        # This could be a quota error or invalid API key
        return []