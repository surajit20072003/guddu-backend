import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import subprocess
import logging
from duckduckgo_search import DDGS

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def detect_needs_latest_info(question: str) -> bool:
    """Detect if question needs up-to-date info"""
    keywords = [
        'latest', 'recent', 'current', 'today', 'now', 'this year',
        'currently', '2024', '2025','2026','2027','happening', 'ongoing',
        'abhi', 'aaj', 'haal', 'present', 'who is', 'price', 'score', 'winner'
    ]
    topics = [
        'news', 'weather', 'stock', 'election', 'president',
        'prime minister', 'ceo', 'match', 'event', 'captain'
    ]
    q_lower = question.lower()
    return any(k in q_lower for k in keywords) or any(t in q_lower for t in topics)

def search_duckduckgo(query: str):
    """Search Web using DuckDuckGo with India Region"""
    try:
        logger.info(f"Searching DuckDuckGo for: {query}")
        
        # Region 'in-en' se India specific news milti hai
        # Backend 'api' fast hota hai
        results = DDGS().text(keywords=query, region='in-en', max_results=3, backend='api')
        
        # Generator to List conversion
        results_list = list(results) if results else []
        
        if not results_list:
            return {'success': False, 'error': 'No results found'}
            
        context_text = ""
        sources = []
        
        for res in results_list:
            title = res.get('title', 'No Title')
            # Library update ke baad kabhi 'body' to kabhi 'snippet' key aati hai
            body = res.get('body', res.get('snippet', ''))
            link = res.get('href', '#')
            
            context_text += f"Source: {title}\nInfo: {body}\n\n"
            sources.append({'title': title, 'url': link})
            
        return {
            'success': True,
            'context': context_text,
            'sources': sources
        }

    except Exception as e:
        logger.error(f"DDG Search error: {str(e)}")
        return {'success': False, 'error': str(e)}

def parse_ollama_response(output: str) -> str:
    try:
        cleaned = output.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict) and 'response' in parsed:
            return parsed['response']
        return str(parsed)
    except:
        return output.strip()

def run_ollama(prompt: str, context: str = None, model: str = "qwen:7b", timeout: int = 90) -> str:
    """Run Ollama with Context"""
    
    if context:
        final_prompt = f"""Use the Search Context to answer.
        
Search Context:
{context}

Question: {prompt}

Instructions:
1. Answer strictly based on the Context.
2. If the context says "Droupadi Murmu", use that name.
3. Be concise."""
    else:
        final_prompt = f"Question: {prompt}\nAnswer concisely."
    
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=final_prompt,
            text=True,
            capture_output=True,
            timeout=timeout
        )
        if result.returncode != 0: return f"Error: {result.stderr}"
        return parse_ollama_response(result.stdout)
    except Exception as e:
        return f"Error: {str(e)}"

@csrf_exempt
def chat_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    try:
        data = json.loads(request.body)
        question = data.get('question', '').strip()
        
        if not question: return JsonResponse({'error': 'No question'}, status=400)

        needs_search = detect_needs_latest_info(question)
        source = "Ollama Knowledge"
        web_sources = []
        answer = ""

        if needs_search:
            search_data = search_duckduckgo(question)
            if search_data['success']:
                answer = run_ollama(question, context=search_data['context'])
                source = "DuckDuckGo + Ollama"
                web_sources = search_data['sources']
            else:
                answer = run_ollama(question)
                source = "Ollama (Search Failed)"
        else:
            answer = run_ollama(question)

        return JsonResponse({
            'question': question,
            'answer': answer,
            'source': source,
            'web_sources': web_sources
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)