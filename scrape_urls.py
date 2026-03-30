import subprocess
import json
import os
import re

# Array of URLs to scrape
URLS = [
    "https://portale.units.it/it/ateneo/campus",
    "https://portale.units.it/it/ateneo/campus/trieste/piazzale-europa-polo/aula-informatica",
    "https://lauree.units.it/it/0320106200800001/il-corso",
    "https://lauree.units.it/it/0320106200800001/come-iscriversi",
    "https://www.biologia.units.it/index.php?/corsi/5/Laurea-in-Scienze-e-Tecnologie-per-lambiente-e-la-natura",
    "https://portale.units.it/it/studiare/contributi/lauree-magistrali-e-magistrali-ciclo-unico",
    "https://portale.units.it/it/studiare/contributi/lauree-magistrali-e-magistrali-ciclo-unico",
    "https://portale.units.it/it/terza-missione/sostenibilita",
    "https://degree.units.it/it/0320106203600002/area-studenti/calendario-didattico",
    "https://degree.units.it/it/0320106202400001/area-studenti/calendario-didattico",
    "https://portale.units.it/en/study/degree-courses"
]

# the last page in incomplete so it requires a custom scraper

OUTPUT_DIR = "scraper_results"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "html_contents.jsonl")

def extract_title(html: str) -> str:
    """Extract the <title> tag content from HTML."""
    match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    if match:
        # Pulisce eventuali spazi o newline
        return match.group(1).strip()
    return "Università di Trieste"

def fetch_html(url: str) -> str:
    """Fetch HTML content from a URL using curl."""
    result = subprocess.run(
        [
            "curl",
            "-s",                  # Silent mode
            "-L",                  # Follow redirects
            "--max-time", "30",    # Timeout after 30 seconds
            "-A", "Mozilla/5.0",   # Set a user-agent to avoid basic blocks
            url,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed with code {result.returncode}: {result.stderr.strip()}")
    return result.stdout


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Deduplicate while preserving order, to avoid scraping the same URL twice
    seen = set()
    unique_urls = []
    for url in URLS:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for url in unique_urls:
            print(f"Fetching: {url}")
            try:
                html = fetch_html(url)
                title = extract_title(html)
                record = {
                    "url": url, 
                    "title": title,
                    "content": html
                    }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                print(f"  OK — {len(html)} chars")
            except Exception as e:
                # Write an error record so the URL is still tracked in the output
                record = {"url": url, "content": None, "error": str(e)}
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                print(f"  ERROR — {e}")

    print(f"\nDone. Results saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()