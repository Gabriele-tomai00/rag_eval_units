import json
import os
import re
import hashlib
from urllib.parse import urlparse
from lxml import html as lxml_html
import html2text
import argparse

# -------------------------------
# Filters
# -------------------------------

REMOVE_IDS = ["footer", "navbar-main", "readspeaker_button"]
REMOVE_CLASSES = ["sidebar", "breadcrumb", "menu", "language-link", "visually-hidden-focusable", "visually-hidden"]
REMOVE_TAGS = [
    "footer", "style", "script", "noscript",
    "button", "svg", "form", "input", "label"
]

# Output folders
OUTPUT_FOLDER = "md_results"
MD_FOLDER = os.path.join(OUTPUT_FOLDER, "md_files")
os.makedirs(MD_FOLDER, exist_ok=True)

# -------------------------------
# Helper functions
# -------------------------------

def sanitize_filename(url: str) -> str:
    """Transform URL into a safe filename."""
    parsed = urlparse(url)
    name = parsed.netloc + parsed.path
    name = re.sub(r"[\\/?:*\"<>|]", "_", name).strip("_")
    if len(name) > 150:
        digest = hashlib.sha1(name.encode()).hexdigest()[:8]
        name = name[:150] + "_" + digest
    return name + ".md"

def clean_html(html_content: str) -> str:
    try:
        tree = lxml_html.fromstring(html_content)
    except Exception:
        return html_content  # fallback: return raw HTML

    for id_val in REMOVE_IDS:
        for el in tree.xpath(f'//*[@id="{id_val}"]'):
            el.drop_tree()

    for cls in REMOVE_CLASSES:
        for el in tree.xpath(f'//*[contains(concat(" ", normalize-space(@class), " "), " {cls} ")]'):
            el.drop_tree()

    for tag in REMOVE_TAGS:
        for el in tree.xpath(f"//{tag}"):
            el.drop_tree()

    return lxml_html.tostring(tree, encoding="unicode")

def html_to_markdown(html_content: str) -> str:
    """Convert HTML to Markdown using html2text."""
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    h.body_width = 0
    return h.handle(html_content)

# -------------------------------
# Main processing
# -------------------------------

def process_jsonl(input_file: str, output_file: str, save_md: bool = False):
    saved = 0
    skipped_duplicates = 0
    seen_content_hashes = set()

    with open(input_file, "r", encoding="utf-8") as fin, \
         open(output_file, "w", encoding="utf-8") as fout:

        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue

            html_content = item.get("content", "")
            url = item.get("url", "unknown")
            item["title"] = item.get("title", "")
            cleaned_html = clean_html(html_content)
            md_text = html_to_markdown(cleaned_html)

            # --- Deduplication: skip pages with identical content (exact MD5 match) ---
            content_hash = hashlib.md5(md_text.encode()).hexdigest()
            if content_hash in seen_content_hashes:
                skipped_duplicates += 1
                continue
            seen_content_hashes.add(content_hash)

            item["content"] = md_text

            if save_md:
                filename = sanitize_filename(url)
                with open(os.path.join(MD_FOLDER, filename), "w", encoding="utf-8") as fmd:
                    fmd.write(md_text)

            fout.write(json.dumps(item, ensure_ascii=False) + "\n")
            saved += 1

    print(f"Process completed.")
    print(f"  Saved pages        : {saved}")
    print(f"  Skipped duplicates : {skipped_duplicates}")
    print(f"  JSONL output       : {output_file}")
    if save_md:
        print(f"  Markdown files     : {MD_FOLDER}")


if __name__ == "__main__":
    print("Start converting HTML documents to MARKDOWN")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", "-i",
        default="scraper_results/html_contents.jsonl",
        help="Input JSONL file (default: scraper_results/html_contents.jsonl)"
    )
    parser.add_argument(
        "--output", "-o",
        default="md_results/cleaned_pages.jsonl",
        help="Output JSONL file (default: md_results/cleaned_pages.jsonl)"
    )
    parser.add_argument(
        "--all",
        "-a",
        default=0,
        type=bool,
        help="Save each page as a separate .md file (default: 0, set to 1 to enable)"
    )
    args = parser.parse_args()

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    process_jsonl(args.input, args.output, save_md=args.all)