import requests
import re
import io
import os
from bs4 import BeautifulSoup
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")


def get_doc_data(url):
    """Extracts title and content from Google Docs or Cloudinary PDFs."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    try:
        if url.endswith('.pdf') or 'raw/upload' in url:
            response = requests.get(url, headers=headers)
            remote_file = io.BytesIO(response.content)
            reader = PdfReader(remote_file)
            text = "".join([page.extract_text() + "\n" for page in reader.pages])
            title = text.split('\n')[0][:50] if text else "Extracted PDF"
            return title, text

        doc_id_match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
        if doc_id_match:
            doc_id = doc_id_match.group(1)
            preview_res = requests.get(
                f"https://docs.google.com/document/d/{doc_id}/preview", headers=headers
            )
            soup = BeautifulSoup(preview_res.text, 'html.parser')
            title = soup.title.string.replace(" - Google Docs", "").strip() if soup.title else "Untitled Doc"
            content_res = requests.get(
                f"https://docs.google.com/document/export?id={doc_id}&exportFormat=txt", headers=headers
            )
            return title, content_res.text

        return None, None
    except Exception as e:
        print(f"⚠️ Fetch Error: {e}")
        return None, None


def search_youtube_for_topic(topic, max_results=10):
    """
    Search YouTube for top-performing videos on this topic.
    Returns a list of video details including their tags, titles, view counts.
    """
    print(f"🔴 [YouTube] Searching for top videos: '{topic}'")
    
    search_url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": topic,
        "type": "video",
        "order": "viewCount",  # Most viewed = proven demand
        "maxResults": max_results,
        "relevanceLanguage": "en",
        "key": YOUTUBE_API_KEY
    }
    
    try:
        resp = requests.get(search_url, params=params).json()
        video_ids = [item["id"]["videoId"] for item in resp.get("items", [])]
        
        if not video_ids:
            print("⚠️ No YouTube results found.")
            return []
        
        # Now fetch tags + stats for those videos
        details_url = "https://www.googleapis.com/youtube/v3/videos"
        details_params = {
            "part": "snippet,statistics",
            "id": ",".join(video_ids),
            "key": YOUTUBE_API_KEY
        }
        details_resp = requests.get(details_url, params=details_params).json()
        
        videos = []
        for item in details_resp.get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            videos.append({
                "title": snippet.get("title", ""),
                "tags": snippet.get("tags", []),  # REAL tags used by top creators
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "video_id": item["id"]
            })
        
        # Sort by views descending
        videos.sort(key=lambda x: x["views"], reverse=True)
        print(f"✅ [YouTube] Found {len(videos)} videos. Top video: {videos[0]['title'][:60] if videos else 'N/A'}")
        return videos
        
    except Exception as e:
        print(f"🔴 YouTube API Error: {e}")
        return []


def extract_real_competitor_tags(videos):
    """
    Aggregates all tags from competitor videos, ranked by frequency.
    These are REAL tags that are proven to rank on YouTube.
    """
    tag_frequency = {}
    
    for video in videos:
        for tag in video.get("tags", []):
            tag_lower = tag.lower().strip()
            if len(tag_lower) > 1:  # skip single-char tags
                tag_frequency[tag_lower] = tag_frequency.get(tag_lower, 0) + 1
    
    # Sort by frequency - most common = most used by successful creators
    sorted_tags = sorted(tag_frequency.items(), key=lambda x: x[1], reverse=True)
    return sorted_tags  # list of (tag, frequency) tuples


def get_people_also_ask(topic):
    """Fetch real search questions people ask about this topic."""
    if not SERPER_API_KEY:
        return []
    
    url = "https://google.serper.dev/search"
    payload = {"q": f"site:youtube.com {topic}", "tbs": "qdr:w"}
    headers = {"X-API-KEY": SERPER_API_KEY}
    
    try:
        response = requests.post(url, json=payload, headers=headers).json()
        questions = [q.get("question") for q in response.get("peopleAlsoAsk", []) if q.get("question")]
        return questions
    except Exception as e:
        print(f"⚠️ Serper Error: {e}")
        return []


def do_full_research(title):
    """
    Master research function. Returns everything needed for SEO:
    - competitor_videos: top performing videos with their real tags
    - competitor_tags: ranked list of (tag, frequency) from those videos  
    - questions: what people are searching/asking
    """
    print(f"\n🔬 Starting full research for: '{title}'")
    
    videos = search_youtube_for_topic(title, max_results=15)
    competitor_tags = extract_real_competitor_tags(videos)
    questions = get_people_also_ask(title)
    
    print(f"📊 Research complete: {len(videos)} videos, {len(competitor_tags)} unique tags, {len(questions)} questions")
    
    return {
        "competitor_videos": videos,
        "competitor_tags": competitor_tags,  # (tag, frequency) tuples
        "questions": questions
    }
