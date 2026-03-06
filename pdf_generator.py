import os
import tempfile
import cloudinary.uploader
from fpdf import FPDF
from dotenv import load_dotenv

load_dotenv()

SOURCE_COLORS = {
    "competitor_proven": (34, 197, 94),
    "script_specific":   (59, 130, 246),
    "search_question":   (234, 179, 8),
}
SOURCE_LABELS = {
    "competitor_proven": "PROVEN",
    "script_specific":   "UNIQUE",
    "search_question":   "SEARCH",
}


def sanitize(text):
    replacements = {
        "\u2014": "-", "\u2013": "-", "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"', "\u2022": "*", "\u2026": "...",
        "\u2012": "-", "\u2015": "-", "\u25bc": "v", "\u25b2": "^",
    }
    text = str(text)
    for char, rep in replacements.items():
        text = text.replace(char, rep)
    return text.encode("latin-1", "ignore").decode("latin-1")


class PDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 11)
        self.set_fill_color(15, 15, 15)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, "  SEO PACKAGE - Powered by Real YouTube Data", 0, 1, "L", fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(3)

    def footer(self):
        # Axigrade logo — bottom right
        try:
            logo_x = self.w - 30   # 30mm from right edge
            logo_y = self.h - 18   # 18mm from bottom
            self.image("axigrade.svg", x=logo_x, y=logo_y, w=20)
        except Exception:
            pass

        self.set_y(-12)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 6, f"Page {self.page_no()} | Tags sourced from real competitor analysis", 0, 0, "C")

    def section_title(self, text, fill_rgb=(230, 230, 230)):
        self.set_fill_color(*fill_rgb)
        self.set_font("helvetica", "B", 11)
        self.set_text_color(0, 0, 0)
        self.cell(0, 8, sanitize(f"  {text}"), 0, 1, "L", fill=True)
        self.ln(2)

    def body_text(self, text, size=9):
        self.set_font("helvetica", "", size)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5, sanitize(str(text)), border=1)
        self.ln(3)

    def numbered_item(self, number, text, fill_rgb=(245, 245, 245)):
        self.set_fill_color(*fill_rgb)
        self.set_font("helvetica", "B", 9)
        self.set_text_color(0, 0, 0)
        self.cell(8, 6, f"{number}.", 0, 0)
        self.set_font("helvetica", "", 9)
        self.multi_cell(0, 6, sanitize(str(text)), border=0, fill=True)
        self.ln(1)

    def tag_pill(self, tag, source):
        color = SOURCE_COLORS.get(source, (180, 180, 180))
        label = SOURCE_LABELS.get(source, "?")
        self.set_font("helvetica", "B", 7)
        self.set_fill_color(*color)
        self.set_text_color(255, 255, 255)
        tag_text = sanitize(f" [{label}] {tag} ")
        tag_w = min(self.get_string_width(tag_text) + 4, 90)
        if self.get_x() + tag_w > self.w - self.r_margin:
            self.ln(7)
        self.cell(tag_w, 6, tag_text, 0, 0, "L", fill=True)
        self.cell(3, 6, "", 0, 0)


def build_and_upload_pdf(seo_data):
    print("Building PDF...")
    fd, temp_path = tempfile.mkstemp(suffix=".pdf")

    try:
        pdf = PDF()
        pdf.set_auto_page_break(auto=True, margin=18)
        pdf.set_margins(12, 12, 12)

        # ── PAGE 1: COVER + COMPETITOR INTELLIGENCE ──────────────────
        pdf.add_page()

        pdf.set_font("helvetica", "B", 18)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 10, sanitize(seo_data.get("title", "")), 0, "C")
        pdf.ln(5)

        pdf.set_font("helvetica", "", 9)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 6,
            f"Total Tags: {seo_data.get('total_tags', 0)}  |  "
            f"Proven: {seo_data.get('proven_count', 0)}  |  "
            f"Script-Specific: {seo_data.get('script_count', 0)}  |  "
            f"Search Questions: {seo_data.get('question_count', 0)}",
            0, 1, "C")
        pdf.ln(6)

        # Legend
        pdf.section_title("TAG COLOR LEGEND", fill_rgb=(245, 245, 245))
        pdf.set_font("helvetica", "", 9)
        desc_map = {
            "competitor_proven": "Used by top-ranking videos on this topic (real YouTube data)",
            "script_specific":   "Specific to your video's unique angle (AI analysis of your script)",
            "search_question":   "What people are actively searching/asking right now",
        }
        for source, color in SOURCE_COLORS.items():
            label = SOURCE_LABELS[source]
            pdf.set_fill_color(*color)
            pdf.cell(22, 6, f" {label} ", 0, 0, "L", fill=True)
            pdf.set_text_color(30, 30, 30)
            pdf.cell(0, 6, f"  - {desc_map[source]}", 0, 1)
            pdf.ln(1)
        pdf.ln(4)

        # Competitor Intelligence
        pdf.section_title("TOP COMPETING VIDEOS (Source of Proven Tags)", fill_rgb=(220, 240, 220))
        pdf.set_font("helvetica", "", 9)
        for i, v in enumerate(seo_data.get("competitor_summary", []), 1):
            vt = sanitize(v["title"])
            pdf.set_text_color(0, 0, 0)
            pdf.cell(6, 6, f"{i}.", 0, 0)
            pdf.set_font("helvetica", "B", 9)
            pdf.cell(0, 6, vt, 0, 1)
            pdf.set_font("helvetica", "", 8)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(6, 5, "", 0, 0)
            pdf.cell(0, 5, f"{v['views']} views  |  {v['video_url']}", 0, 1)
            pdf.ln(1)
        pdf.ln(4)

        if seo_data.get("ai_reasoning"):
            pdf.section_title("WHY THESE TAGS WERE CHOSEN", fill_rgb=(220, 230, 255))
            pdf.body_text(seo_data["ai_reasoning"])

        # ── PAGE 2: TAGS ──────────────────────────────────────────────
        pdf.add_page()
        pdf.section_title("COMPLETE TAG LIST (Copy-Paste Ready)", fill_rgb=(240, 240, 240))

        pdf.set_font("helvetica", "B", 8)
        pdf.set_text_color(0, 80, 0)
        pdf.cell(0, 6, ">> COPY THIS BLOCK DIRECTLY INTO YOUTUBE:", 0, 1)
        pdf.set_font("helvetica", "", 8)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 5, sanitize(seo_data.get("tag_string", "")), border=1)
        pdf.ln(6)

        pdf.section_title("TAG BREAKDOWN BY SOURCE", fill_rgb=(240, 240, 240))
        for source_key in ["competitor_proven", "script_specific", "search_question"]:
            source_tags = [t for t in seo_data.get("tags", []) if t["source"] == source_key]
            if not source_tags:
                continue
            label = SOURCE_LABELS[source_key]
            pdf.set_font("helvetica", "B", 9)
            pdf.set_text_color(50, 50, 50)
            pdf.cell(0, 7, f"{label} TAGS ({len(source_tags)})", 0, 1)
            for t in source_tags:
                pdf.tag_pill(sanitize(t["tag"]), source_key)
            pdf.ln(9)
            pdf.set_text_color(0, 0, 0)

        # ── PAGES 3+: STRATEGIES ──────────────────────────────────────
        for i, strategy in enumerate(seo_data.get("strategies", []), 1):
            pdf.add_page()

            stype = sanitize(strategy.get("type", "Strategy"))
            pdf.set_font("helvetica", "B", 14)
            pdf.set_fill_color(20, 20, 20)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 12, f"  STRATEGY {i}: {stype.upper()}", 0, 1, "L", fill=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(4)

            # Description
            pdf.section_title("VIDEO DESCRIPTION")
            pdf.body_text(strategy.get("description", ""))

            # 3 Pinned Comments
            pdf.section_title("PINNED COMMENTS (Post immediately after publishing — pick 1 or rotate)", fill_rgb=(255, 240, 200))
            pinned_comments = strategy.get("pinned_comments", [])
            if isinstance(pinned_comments, list):
                for j, comment in enumerate(pinned_comments, 1):
                    pdf.numbered_item(j, comment, fill_rgb=(255, 250, 230))
            else:
                pdf.body_text(pinned_comments)
            pdf.ln(2)

            # 3 Community Posts
            pdf.section_title("COMMUNITY POSTS (Schedule across upload week)", fill_rgb=(220, 240, 255))
            community_posts = strategy.get("community_posts", [])
            if isinstance(community_posts, list):
                for j, post in enumerate(community_posts, 1):
                    if isinstance(post, dict):
                        # Always reset X to left margin before any cell/multi_cell
                        pdf.set_x(pdf.l_margin)
                        pdf.set_font("helvetica", "B", 9)
                        pdf.set_text_color(0, 0, 0)
                        pdf.set_fill_color(210, 230, 255)
                        pdf.cell(0, 7, f"  Post {j}", 0, 1, fill=True)

                        pdf.set_x(pdf.l_margin)
                        pdf.set_font("helvetica", "B", 8)
                        pdf.set_text_color(30, 30, 150)
                        pdf.cell(0, 5, "  Caption:", 0, 1)

                        pdf.set_x(pdf.l_margin)
                        pdf.set_font("helvetica", "", 9)
                        pdf.set_text_color(30, 30, 30)
                        pdf.multi_cell(0, 5, sanitize(post.get("caption", "")), border=0)

                        pdf.set_x(pdf.l_margin)
                        pdf.set_font("helvetica", "B", 8)
                        pdf.set_text_color(130, 30, 150)
                        pdf.cell(0, 5, "  Image Prompt (Midjourney / DALL-E):", 0, 1)

                        pdf.set_x(pdf.l_margin)
                        pdf.set_font("helvetica", "I", 8)
                        pdf.set_text_color(80, 80, 80)
                        pdf.multi_cell(0, 5, sanitize(post.get("image_prompt", "")), border=1)
                        pdf.ln(4)
                    else:
                        pdf.numbered_item(j, str(post))
            else:
                pdf.body_text(community_posts)

        pdf.output(temp_path)

        res = cloudinary.uploader.upload(temp_path, resource_type="raw")
        print(f"PDF ready: {res['secure_url']}")
        return res["secure_url"]

    finally:
        os.close(fd)
        if os.path.exists(temp_path):
            os.remove(temp_path)