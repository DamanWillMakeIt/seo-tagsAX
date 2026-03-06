# SEO-TAGS v2 — YouTube SEO Agent

Generates a fully transparent, data-grounded SEO package for YouTube videos.
Tags are sourced from **real competitor YouTube data** — not AI guesswork.

---

## Setup

1. Copy `.env.example` to `.env` and fill in your API keys:
   - `GEMINI_API_KEY` — Google Gemini
   - `YOUTUBE_API_KEY` — YouTube Data API v3 (**new in v2**)
   - `SERPER_API_KEY` — Serper (for People Also Ask)
   - Cloudinary credentials — for PDF hosting

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the server:
   ```bash
   python app.py
   ```

---

## API Usage

**POST** `/architect/seo`

```json
{
  "title": "Dhoni's Secret Strategy",
  "script": "In this video we cover..."
}
```

Or with a Google Doc / Cloudinary PDF link:

```json
{
  "doc_link": "https://docs.google.com/document/d/YOUR_ID/edit"
}
```

**Response:**
```json
{
  "status": "success",
  "pdf_url": "https://res.cloudinary.com/...",
  "title_used": "Dhoni's Secret Strategy",
  "total_tags": 38,
  "proven_tags": 22,
  "script_tags": 11,
  "question_tags": 5
}
```

---

## How Tags Are Built (3 Layers)

| Color | Label | Source |
|-------|-------|--------|
| 🟢 Green | PROVEN | Real tags used by top-ranking competitor videos (YouTube API) |
| 🔵 Blue | UNIQUE | Script-specific tags for your video's unique angle (Gemini) |
| 🟡 Gold | SEARCH | Long-tail tags from real search questions (Serper PAA) |

---

## What's in the PDF

- **Page 1:** Competitor intelligence (top videos + view counts + links)
- **Page 2:** Full tag list — copy-paste block + color-coded breakdown by source
- **Pages 3–5:** 3 metadata strategies (Controversial / Story-Driven / Mystery), each with:
  - Full SEO description (150+ words with tags woven in)
  - Pinned comment
  - Community post
  - AI image prompt

---

## Changes from v1
- Tags now grounded in real YouTube API data (not AI-generated guesses)
- Hidden brand watermark removed
- Every tag labeled by source with reasoning
- Competitor video intelligence included in PDF
- `initial_tags` placeholder fully replaced with live research
