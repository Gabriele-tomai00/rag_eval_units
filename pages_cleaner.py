import json
import os
import re
from urllib.parse import urlparse, unquote
import hashlib
from lxml import html as lxml_html
import html2text
import argparse

# -------------------------------
# filters
# -------------------------------

REMOVE_IDS = ["footer", "navbar-main", "readspeaker_button"]
REMOVE_CLASSES = ["sidebar", "breadcrumb", "menu", "language-link", "visually-hidden-focusable", "visually-hidden"]
REMOVE_TAGS = [
    "footer", "style", "script", "noscript", 
    "button", "svg", "form", "input", "label"
]
# Cartelle di output
OUTPUT_FOLDER = "md_results"
MD_FOLDER = os.path.join(OUTPUT_FOLDER, "md_files")
os.makedirs(MD_FOLDER, exist_ok=True)

# -------------------------------
# helper functions
# -------------------------------

def sanitize_filename(url: str) -> str:
    """Trasforma l'URL in un filename sicuro."""
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
        return html_content  # fallback: ritorna raw HTML

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
            item["content"] = md_text

            if save_md:
                filename = sanitize_filename(url)
                with open(os.path.join(MD_FOLDER, filename), "w", encoding="utf-8") as fmd:
                    fmd.write(md_text)

            fout.write(json.dumps(item, ensure_ascii=False) + "\n")
            saved += 1

    print(f"Process completed: {saved} saved pages.")
    print(f"JSONL output: {output_file}")
    print(f"Markdown files: {MD_FOLDER}")



if __name__ == "__main__":
    print("Start converting HTML documents to MARKDOWN")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="scraper_results/html_contents.jsonl",
        help="File JSONL di input (default: scraper_results/html_contents.jsonl)"
    )
    parser.add_argument(
        "--output",
        default="md_results/cleaned_pages.jsonl",
        help="File JSONL di output (default: md_results/cleaned_pages.jsonl)"
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