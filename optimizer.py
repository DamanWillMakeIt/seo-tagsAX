import time
import os
import json
import re
from google import genai
from google.genai.types import GenerateContentConfig
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# COST TRACKING
# Gemini 2.0 Flash pricing (as of March 2025):
#   Input:  $0.10  per 1,000,000 tokens = $0.0000001  per token
#   Output: $0.40  per 1,000,000 tokens = $0.0000004  per token
# Source: https://ai.google.dev/pricing
COSTS = {
    "gemini_input_per_token":  0.0000001,   # $0.10 / 1M tokens
    "gemini_output_per_token": 0.0000004,   # $0.40 / 1M tokens
    "serper_per_search":       0.001,        # ~$1 per 1000 searches
    "youtube_api_per_unit":    0.0,          # Free up to 10k units/day
    "cloudinary_per_upload":   0.0,          # Free tier
}

_cost_log = []

def _log_cost(service, detail, cost_usd):
    _cost_log.append({"service": service, "detail": detail, "cost_usd": round(cost_usd, 6)})

def get_cost_summary():
    total = sum(e["cost_usd"] for e in _cost_log)
    return {
        "total_usd": round(total, 6),
        "total_display": f"${total:.6f}",
        "breakdown": list(_cost_log),
    }

def reset_costs():
    _cost_log.clear()


def _call_gemini(prompt, label="call", retries=3):
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=GenerateContentConfig(response_mime_type="application/json")
            )

            # Use real token counts from API response (usage_metadata)
            usage = getattr(response, "usage_metadata", None)
            if usage:
                input_tokens  = getattr(usage, "prompt_token_count", 0) or 0
                output_tokens = getattr(usage, "candidates_token_count", 0) or 0
                source = "actual API token count"
            else:
                # Fallback: estimate (~4 chars per token is standard approximation)
                input_tokens  = len(prompt) // 4
                output_tokens = len(response.text) // 4
                source = "estimated from char count"

            cost = (input_tokens  * COSTS["gemini_input_per_token"] +
                    output_tokens * COSTS["gemini_output_per_token"])

            print(f"  [{label}] tokens in={input_tokens} out={output_tokens} ({source}) cost=${cost:.6f}")
            _log_cost(
                "Gemini 2.0 Flash",
                f"{label} | in={input_tokens} out={output_tokens} tokens ({source})",
                cost
            )
            return response
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                wait = 15 * (attempt + 1)
                print(f"Gemini rate limit. Waiting {wait}s (retry {attempt+2}/{retries})...")
                time.sleep(wait)
            else:
                raise


# Common English words that appear in names but are NOT content signals
_NAME_STOPWORDS = {
    "the", "and", "for", "with", "how", "why", "what", "your",
    "motivation", "official", "channel", "show", "podcast", "tv",
}

def _is_tag_relevant(tag, title, script):
    """
    Filter competitor tags that are personal brand / celebrity names
    with no relevance to this video's content.

    Logic:
    1. If ALL meaningful words in the tag appear in the title+script → keep
    2. If the tag looks like a personal name (2-3 Title Case words, none are
       topic/content keywords) AND none of those words appear in title+script → drop
    3. Everything else → keep
    """
    tag_lower = tag.lower()
    content_lower = (title + " " + script[:500]).lower()
    tag_words = [w.lower() for w in tag.split() if len(w) > 2]

    # Step 1: any meaningful word present in content? Keep it.
    content_words = set(re.findall(r"[a-z]+", content_lower))
    if any(w in content_words for w in tag_words if w not in _NAME_STOPWORDS):
        return True

    # Step 2: personal name detection
    # A tag is name-like if it's 2-3 words, each starting with uppercase,
    # and none are common topic/content words
    raw_words = tag.split()
    topic_signals = {
        "money", "finance", "financial", "wealth", "budget", "invest",
        "debt", "saving", "habit", "tips", "income", "tax", "stock",
        "fund", "crypto", "credit", "loan", "salary", "banking", "trading",
        "cricket", "ipl", "match", "strategy", "sports", "health", "fitness",
        "business", "marketing", "startup", "career", "youtube", "video",
        "mistakes", "habits", "rules", "guide", "free", "destroy", "build",
    }
    # Normalise: treat "mel robbins" same as "Mel Robbins" for name detection
    title_case_words = [w.capitalize() for w in raw_words]
    looks_like_name = (
        2 <= len(raw_words) <= 3 and
        not any(kw in tag_lower for kw in topic_signals)
    )
    if looks_like_name:
        # None of the name words appear in the content → irrelevant celebrity tag
        name_words_in_content = [w.lower() for w in raw_words if w.lower() in content_words]
        if not name_words_in_content:
            return False

    return True


def build_tag_list(title, script, research):
    competitor_tags = research.get("competitor_tags", [])
    questions   = research.get("questions", [])

    top_videos_context = "\n".join([
        f"- \"{v['title']}\" ({v['views']:,} views)"
        for v in research.get("competitor_videos", [])[:5]
    ])

    clean_title = re.sub(r'^(PROJECT|TITLE|Niche|Duration):', '', title, flags=re.IGNORECASE).strip()

    # Filter proven tags for relevance BEFORE using them
    raw_proven = [tag for tag, freq in competitor_tags[:35]]
    proven_tags = [t for t in raw_proven if _is_tag_relevant(t, clean_title, script[:2000])][:25]
    dropped = len(raw_proven) - len(proven_tags)


    prompt = (
        "You are a YouTube SEO specialist. Generate tags SPECIFIC to this video's unique angle.\n\n"
        f"VIDEO TITLE: {clean_title}\n"
        f"SCRIPT SNIPPET: {script[:3000]}\n\n"
        f"TOP COMPETING VIDEOS:\n{top_videos_context}\n\n"
        f"WHAT PEOPLE ARE ASKING:\n{questions}\n\n"
        f"ALREADY COVERED (DO NOT duplicate):\n{', '.join(proven_tags[:15])}\n\n"
        "Generate 15-20 tags specific to this video's unique angle. Return ONLY JSON:\n"
        '{"script_specific_tags": ["tag1", ...], "reasoning": "one sentence"}'
    )

    try:
        response = _call_gemini(prompt, label="Tag Generation")
        raw = response.text.strip().lstrip("```json").rstrip("```").strip()
        ai_data = json.loads(raw)
        script_specific_tags = ai_data.get("script_specific_tags", [])
        ai_reasoning         = ai_data.get("reasoning", "")
    except Exception as e:
        print(f"AI tag generation error: {e}")
        script_specific_tags, ai_reasoning = [], ""

    question_tags = []
    for q in questions[:5]:
        if q:
            tag = q.lower().strip().rstrip("?")
            if len(tag) < 80:
                question_tags.append(tag)

    seen, final_tags = set(), []
    for tag in proven_tags:
        t = tag.lower().strip()
        if t not in seen:
            seen.add(t)
            final_tags.append({"tag": tag, "source": "competitor_proven",
                                "why": "Used by top-ranking videos on this topic"})
    for tag in script_specific_tags:
        t = tag.lower().strip()
        if t not in seen:
            seen.add(t)
            final_tags.append({"tag": tag, "source": "script_specific",
                                "why": "Specific to this video's unique angle"})
    for tag in question_tags:
        t = tag.lower().strip()
        if t not in seen:
            seen.add(t)
            final_tags.append({"tag": tag, "source": "search_question",
                                "why": "People are actively searching this question"})

    return final_tags, ai_reasoning


def generate_metadata_strategies(title, script, research, tags):
    clean_title      = re.sub(r'^(PROJECT|TITLE|Niche|Duration):', '', title, flags=re.IGNORECASE).strip()
    questions        = research.get("questions", [])
    top_video_titles = [v["title"] for v in research.get("competitor_videos", [])[:5]]
    tag_string       = ", ".join([t["tag"] for t in tags[:20]])

    schema = (
        '{"strategies": ['
        '{"type": "Controversial (High CTR)", '
        '"description": "150+ word SEO description with tags woven naturally. Hook. Body. CTA.", '
        '"pinned_comments": ["debate-sparking comment", "hot take / strong opinion", "question that gets replies"], '
        '"community_posts": ['
        '{"caption": "short punchy caption", "image_prompt": "detailed AI image prompt"}, '
        '{"caption": "...", "image_prompt": "..."}, '
        '{"caption": "...", "image_prompt": "..."}]}, '
        '{"type": "Story-Driven (Relatable)", "description": "...", '
        '"pinned_comments": ["...", "...", "..."], '
        '"community_posts": [{"caption": "...", "image_prompt": "..."}, {"caption": "...", "image_prompt": "..."}, {"caption": "...", "image_prompt": "..."}]}, '
        '{"type": "Mystery (Curiosity Gap)", "description": "...", '
        '"pinned_comments": ["...", "...", "..."], '
        '"community_posts": [{"caption": "...", "image_prompt": "..."}, {"caption": "...", "image_prompt": "..."}, {"caption": "...", "image_prompt": "..."}]}]}'
    )

    prompt = (
        "You are a YouTube growth strategist. Generate 3 complete metadata strategies.\n\n"
        f"VIDEO TITLE: {clean_title}\n"
        f"SCRIPT: {script[:3000]}\n"
        f"TOP TAGS: {tag_string}\n"
        f"COMPETITOR TITLES: {top_video_titles}\n"
        f"QUESTIONS PEOPLE ASK: {questions}\n\n"
        "Rules:\n"
        "- Each strategy has: description, 3 pinned_comments, 3 community_posts\n"
        "- Pinned comments: under 3 sentences, spark debate/emotion/curiosity, reference the topic specifically\n"
        "- Community posts: each has a short caption (1-2 sentences) + a specific AI image generation prompt\n"
        "- Descriptions: 150+ words, tags woven into sentences naturally (not listed at end)\n"
        "- Be specific to this video topic. No generic filler.\n\n"
        f"Return ONLY valid JSON matching this structure:\n{schema}"
    )

    try:
        response = _call_gemini(prompt, label="Metadata Strategies")
        raw = response.text.strip().lstrip("```json").rstrip("```").strip()
        data = json.loads(raw)
        return data.get("strategies", [])
    except Exception as e:
        print(f"Strategy generation error: {e}")
        return []


def generate_seo_package(title, script, research):
    reset_costs()

    _log_cost("YouTube Data API v3", "Search + Video Details (15 videos)", 0.0)
    if research.get("questions"):
        _log_cost("Serper API", "People Also Ask search", COSTS["serper_per_search"])

    print(f"\nBuilding SEO package for: {title}")

    print("Building tag list from real competitor data + script analysis...")
    tags, ai_reasoning = build_tag_list(title, script, research)

    print("Generating 3 metadata strategies (3 pinned comments + 3 community posts each)...")
    strategies = generate_metadata_strategies(title, script, research, tags)

    _log_cost("Cloudinary", "PDF upload (free tier)", 0.0)

    top_videos = research.get("competitor_videos", [])[:5]
    competitor_summary = [
        {
            "title":     v["title"],
            "views":     f"{v['views']:,}",
            "video_url": f"https://youtube.com/watch?v={v['video_id']}"
        }
        for v in top_videos
    ]

    cost_summary = get_cost_summary()
    print(f"Estimated cost this run: ${cost_summary['total_usd']:.6f}")

    return {
        "title":              title,
        "tags":               tags,
        "tag_string":         ", ".join([t["tag"] for t in tags]),
        "ai_reasoning":       ai_reasoning,
        "strategies":         strategies,
        "competitor_summary": competitor_summary,
        "total_tags":         len(tags),
        "proven_count":       sum(1 for t in tags if t["source"] == "competitor_proven"),
        "script_count":       sum(1 for t in tags if t["source"] == "script_specific"),
        "question_count":     sum(1 for t in tags if t["source"] == "search_question"),
        "cost_summary":       cost_summary,
    }