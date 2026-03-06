from researcher import get_doc_data, do_full_research
from optimizer import generate_seo_package
from pdf_generator import build_and_upload_pdf


def run_seo_agent(input_data):
    title          = input_data.get("title")
    script_content = input_data.get("script")
    doc_link       = input_data.get("doc_link")

    if doc_link and not script_content:
        print("Fetching script from document...")
        extracted_title, script_content = get_doc_data(doc_link)
        if extracted_title and not title:
            title = extracted_title

    if not title:
        raise ValueError("A title is required.")
    if not script_content:
        script_content = ""

    print(f"\nProcessing SEO for: {title}")

    research = do_full_research(title)
    seo_data = generate_seo_package(title, script_content, research)
    pdf_url  = build_and_upload_pdf(seo_data)

    # Full structured response for frontend + PDF URL
    return {
        "status":        "success",
        "pdf_url":       pdf_url,
        "title":         title,
        "total_cost_usd":     seo_data["cost_summary"]["total_usd"],
        "total_cost_display": seo_data["cost_summary"]["total_display"],

        # Tag summary
        "tag_stats": {
            "total":    seo_data["total_tags"],
            "proven":   seo_data["proven_count"],
            "unique":   seo_data["script_count"],
            "search":   seo_data["question_count"],
        },

        # Tag string for direct copy-paste
        "tag_string": seo_data["tag_string"],

        # Why AI chose these tags
        "tag_reasoning": seo_data.get("ai_reasoning", ""),

        # Top competitor videos
        "competitors": seo_data["competitor_summary"],

        # 3 strategies — each has:
        #   type, description, pinned_comments[], community_posts[{caption, image_prompt}]
        "strategies": seo_data["strategies"],

        # Cost breakdown
        "cost_summary": seo_data["cost_summary"],
    }


if __name__ == "__main__":
    import json
    payload = {
        "title": "Dhoni's Secret Strategy",
        "script": "In this video we talk about MS Dhoni's captaincy approach..."
    }
    result = run_seo_agent(payload)
    print(json.dumps(result, indent=2))