"""
Filter cleaned_pages_big.jsonl to produce a smaller clean_corpus.jsonl.

Strategy:
- Always keep URLs listed in MUST_KEEP_URLS (sources from questions_answares.py)
- Keep 100% of core student-facing Italian pages
- Keep 100% of degree.units.it/en (needed for English-language course questions)
- Keep ~7% (1-in-14 sample) of secondary/noisy categories for variety
- Skip duplicate URLs (keep first occurrence only)
"""

import json
import re
import hashlib
from pathlib import Path
from urllib.parse import urlparse

INPUT = Path(__file__).parent / "cleaned_pages_big.jsonl"
OUTPUT = Path(__file__).parent / "clean_corpus.jsonl"

# Sampling ratio for secondary categories (1 = keep all, 14 = keep ~7%)
SAMPLE_EVERY = 14

# URLs that must always be present — sources from questions_answares.py
MUST_KEEP_URLS: set[str] = {
    "https://portale.units.it/it/ateneo/campus",
    "https://portale.units.it/it/ateneo/campus/trieste/piazzale-europa-polo/aula-informatica",
    "https://lauree.units.it/it/0320106200800001/come-iscriversi",
    "https://www.biologia.units.it/index.php?/corsi/5/Laurea-in-Scienze-e-Tecnologie-per-lambiente-e-la-natura",
    "https://portale.units.it/it/studiare/contributi/lauree-magistrali-e-magistrali-ciclo-unico",
    "https://portale.units.it/it/terza-missione/sostenibilita",
    "https://degree.units.it/it/0320106203600002/area-studenti/calendario-didattico",
    "https://degree.units.it/it/0320106202400001/area-studenti/calendario-didattico",
    "https://degree.units.it/it/0320107303300001/area-studenti/insegnamenti/2025/120599/2025/2/10740/2025/13129",
    "https://degree.units.it/en/0320107303300001/students-area/taught-courses/2025/120014/2025/2/10740/2025",
    "https://www.units.it/catalogo-della-didattica-a-distanza",
    "https://amm.units.it/normativa/regolamenti/articolo-22178/art-31-corsi-studio",
    "https://amm.units.it/normativa/regolamenti/articolo-22145/art-1-natura-e-fini",
    "https://amm.units.it/normativa/regolamenti/articolo-53336/art-37-dottore-ricerca-honoris-causa",
    "https://amm.units.it/normativa/regolamenti/articolo-44584/art-29-borse-studio",
    "https://portale.units.it/it/studiare/orientarsi/preparazione-test-area-medico-sanitaria",
    "https://lauree.units.it/it/0320107304700001/area-studenti/tirocinio-e-internato",
    "https://lauree.units.it/it/0320106203000001/area-studenti/tirocinio-e-internato",
    "https://lauree.units.it/it/0320106201300002/area-studenti/tirocinio-e-internato",
}


def url_bucket(url: str) -> int:
    """Deterministic 0-based bucket for a URL (0 to SAMPLE_EVERY-1)."""
    return int(hashlib.md5(url.encode()).hexdigest(), 16) % SAMPLE_EVERY


def classify(url: str) -> str:
    """
    Returns:
      'keep'    — always keep
      'sample'  — keep only 1 in SAMPLE_EVERY
    """
    parsed = urlparse(url)
    netloc = parsed.netloc.rstrip(":443").rstrip(":80")
    path = parsed.path or "/"

    # ── Always keep: core student-facing Italian content ──────────────────────
    if netloc == "portale.units.it" and path.startswith("/it/"):
        return "keep"
    if netloc == "lauree.units.it" and path.startswith("/it/"):
        # Individual insegnamenti pages are noisy → sample
        if re.match(r"^/it/\d+/area-studenti/insegnamenti/.+", path):
            return "sample"
        return "keep"
    if netloc == "degree.units.it":
        return "keep"  # keep both /it/ and /en/ (Cybersecurity question needs /en/)
    if netloc == "amm.units.it" and path.startswith("/normativa"):
        return "keep"
    if netloc == "amm.units.it" and path.startswith("/placement"):
        return "keep"
    if netloc == "phd.units.it" and path.startswith("/it"):
        return "keep"
    if netloc == "www.biologia.units.it":
        return "keep"
    if netloc == "www.units.it" and path.startswith("/catalogo"):
        return "keep"
    if netloc == "bartoli.inginf.units.it":
        return "keep"

    # ── Sample: secondary / noisy categories ──────────────────────────────────
    return "sample"


def main():
    stats: dict[str, int] = {
        "must_keep": 0,
        "keep": 0,
        "sample_kept": 0,
        "sample_dropped": 0,
        "duplicates": 0,
    }
    seen_urls: set[str] = set()

    with open(INPUT, encoding="utf-8") as fin, open(OUTPUT, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            doc = json.loads(line)
            url = doc.get("url", "")

            if url in seen_urls:
                stats["duplicates"] += 1
                print("URL DUPLICATE (skipping):", url)
                continue
            seen_urls.add(url)

            if url in MUST_KEEP_URLS:
                fout.write(line + "\n")
                stats["must_keep"] += 1
                continue

            decision = classify(url)
            if decision == "keep":
                fout.write(line + "\n")
                stats["keep"] += 1
            else:  # "sample"
                if url_bucket(url) == 0:
                    fout.write(line + "\n")
                    stats["sample_kept"] += 1
                else:
                    stats["sample_dropped"] += 1

    total_in = stats["must_keep"] + stats["keep"] + stats["sample_kept"] + stats["sample_dropped"] + stats["duplicates"]
    total_out = stats["must_keep"] + stats["keep"] + stats["sample_kept"]
    print(f"Input:          {total_in:>6} documents")
    print(f"Must-kept:      {stats['must_keep']:>6}  (pinned eval sources)")
    print(f"Always-kept:    {stats['keep']:>6}")
    print(f"Sampled-kept:   {stats['sample_kept']:>6}  (~1 in {SAMPLE_EVERY} of secondary)")
    print(f"Dropped:        {stats['sample_dropped']:>6}")
    print(f"Duplicates:     {stats['duplicates']:>6}  (skipped)")
    print(f"Output:         {total_out:>6} documents ({total_out/total_in*100:.1f}% of input)")
    print(f"Written to:     {OUTPUT}")


if __name__ == "__main__":
    main()
