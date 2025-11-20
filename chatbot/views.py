
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import subprocess
import requests
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def detect_needs_latest_info(question: str) -> bool:
    """Detect if question needs up-to-date info"""
    keywords = [
        'latest', 'recent', 'current', 'today', 'now', 'this year',
        'currently', '2024', '2025', 'happening', 'ongoing',
        'abhi', 'aaj', 'haal', 'present'
    ]
    topics = [
        'news', 'weather', 'price', 'stock', 'election', 'president',
        'prime minister', 'ceo', 'score', 'match', 'event', 'captain'
    ]
    q_lower = question.lower()
    return any(k in q_lower for k in keywords) or any(t in q_lower for t in topics)

def search_wikipedia(query: str):
    """Search Wikipedia using MediaWiki API - most reliable method"""
    try:
        base_url = "https://en.wikipedia.org/w/api.php"
        
        # Step 1: Search for the page
        search_params = {
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'srsearch': query,
            'srlimit': 5,
            'utf8': 1
        }
        
        headers = {
            'User-Agent': 'DjangoChatBot/1.0 (Educational Purpose)'
        }
        
        logger.info(f"Wikipedia search query: {query}")
        search_response = requests.get(base_url, params=search_params, headers=headers, timeout=10)
        
        # Check if response is valid
        if search_response.status_code != 200:
            logger.error(f"Wikipedia search failed with status {search_response.status_code}")
            return {'success': False, 'error': f'HTTP {search_response.status_code}'}
        
        # Check if response is JSON
        try:
            search_data = search_response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Wikipedia returned non-JSON: {search_response.text[:200]}")
            return {'success': False, 'error': 'Wikipedia returned invalid JSON'}
        
        results = search_data.get('query', {}).get('search', [])
        
        if not results:
            logger.info("No Wikipedia results found")
            return {'success': False, 'error': 'No results found'}
        
        # Get first result's title
        page_title = results[0]['title']
        logger.info(f"Found Wikipedia page: {page_title}")
        
        # Step 2: Get page content using extracts
        content_params = {
            'action': 'query',
            'format': 'json',
            'titles': page_title,
            'prop': 'extracts|info',
            'exintro': True,
            'explaintext': True,
            'inprop': 'url',
            'utf8': 1
        }
        
        content_response = requests.get(base_url, params=content_params, headers=headers, timeout=10)
        
        if content_response.status_code != 200:
            logger.error(f"Wikipedia content fetch failed with status {content_response.status_code}")
            return {'success': False, 'error': f'Content fetch failed: HTTP {content_response.status_code}'}
        
        try:
            content_data = content_response.json()
        except json.JSONDecodeError:
            logger.error(f"Wikipedia content returned non-JSON: {content_response.text[:200]}")
            return {'success': False, 'error': 'Wikipedia content invalid JSON'}
        
        # Extract page data
        pages = content_data.get('query', {}).get('pages', {})
        
        if not pages:
            return {'success': False, 'error': 'No page data returned'}
        
        page_id = list(pages.keys())[0]
        page_info = pages[page_id]
        
        # Check if page exists (not missing)
        if 'missing' in page_info:
            return {'success': False, 'error': 'Page not found'}
        
        extract = page_info.get('extract', '')
        page_url = page_info.get('fullurl', f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}")
        
        if not extract or len(extract.strip()) < 50:
            return {'success': False, 'error': 'Empty or too short content'}
        
        logger.info(f"Successfully fetched Wikipedia content ({len(extract)} chars)")
        
        return {
            'success': True,
            'title': page_title,
            'summary': extract[:2000],  # Limit to 2000 chars
            'url': page_url
        }
        
    except requests.Timeout:
        logger.error("Wikipedia request timeout")
        return {'success': False, 'error': 'Request timeout'}
    except requests.RequestException as e:
        logger.error(f"Wikipedia request error: {str(e)}")
        return {'success': False, 'error': f'Network error: {str(e)}'}
    except Exception as e:
        logger.error(f"Unexpected error in Wikipedia search: {str(e)}")
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}

def parse_ollama_response(output: str) -> str:
    """Parse JSON response from Ollama and extract answer"""
    try:
        # Remove markdown code blocks
        cleaned = output.replace("```json", "").replace("```", "").strip()
        
        # Try to parse as JSON
        parsed = json.loads(cleaned)
        
        # Extract response field
        if isinstance(parsed, dict) and 'response' in parsed:
            return parsed['response']
        
        return str(parsed)
    except json.JSONDecodeError:
        # If not JSON, return as-is (Ollama sometimes gives direct text)
        return output.strip()

def run_ollama(prompt: str, model: str = "qwen:7b", timeout: int = 90) -> str:
    """Run Ollama model and return parsed answer"""
    forced_prompt = f"""You are a helpful AI assistant. Answer concisely and accurately.

Question: {prompt}

Provide a clear answer in 2-3 sentences maximum."""
    
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=forced_prompt,
            text=True,
            capture_output=True,
            timeout=timeout
        )
        
        if result.returncode != 0:
            logger.error(f"Ollama error: {result.stderr}")
            return f"Ollama error: {result.stderr}"
        
        output = result.stdout.strip()
        return parse_ollama_response(output)
        
    except subprocess.TimeoutExpired:
        logger.error("Ollama timeout")
        return "Request timeout - please try again"
    except FileNotFoundError:
        logger.error("Ollama not found")
        return "Ollama service not available"
    except Exception as e:
        logger.error(f"Ollama exception: {str(e)}")
        return f"Error: {str(e)}"

def extract_answer_from_wiki(wiki_data, question: str) -> str:
    """Use Ollama to extract answer from Wikipedia summary"""
    if not wiki_data['success']:
        return None
    
    prompt = f"""Based on the Wikipedia information below, answer this question concisely:

Question: {question}

Wikipedia Summary:
{wiki_data['summary']}

Answer in 1-2 sentences based ONLY on the information provided above."""
    
    answer = run_ollama(prompt, timeout=60)
    return answer



@csrf_exempt
def chat_api(request):
    """POST API endpoint using Ollama with Wikipedia integration"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)

    try:
        data = json.loads(request.body)
        question = data.get('question', '').strip()
        
        if not question:
            return JsonResponse({'error': 'Question is required'}, status=400)

        needs_latest = detect_needs_latest_info(question)
        wiki_url = None
        source = "Ollama Model"
        wiki_title = None

        if needs_latest:
            logger.info(f"Question needs latest info: {question}")
            # Try Wikipedia for current information
            wiki_data = search_wikipedia(question)
            
            if wiki_data['success']:
                logger.info("Wikipedia search successful")
                answer = extract_answer_from_wiki(wiki_data, question)
                source = "Wikipedia + Ollama"
                wiki_url = wiki_data.get('url')
                wiki_title = wiki_data.get('title')
            else:
                logger.warning(f"Wikipedia failed: {wiki_data.get('error')}")
                # Fallback to pure Ollama
                answer = run_ollama(question)
                source = f"Ollama Model (Wiki: {wiki_data.get('error', 'unavailable')})"
        else:
            # General knowledge question
            answer = run_ollama(question)

        response_data = {
            'question': question,
            'answer': answer,
            'source': source,
            'needs_latest': needs_latest
        }
        
        # Add wiki info only if available
        if wiki_url:
            response_data['wiki_url'] = wiki_url
            response_data['wiki_title'] = wiki_title
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request'}, status=400)
    except Exception as e:
        logger.error(f"Chat API error: {str(e)}")
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)