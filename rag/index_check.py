import json
import chromadb
from pathlib import Path

JSONL_FILE = "../md_results/cleaned_pages_big.jsonl"
CHROMA_PATHS = [
    "index_markdown_and_sentence_big_512",
    "index_markdown_big",
    "index_sentence_big_512"
]


def audit_index(chroma_path: str, expected_urls: set) -> None:
    if not Path(chroma_path).exists():
        print(f"{chroma_path} — folder not found, skipping.\n")
        return

    print(f"Connecting to ChromaDB at: {chroma_path}...")
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_collection("quickstart")

    all_ids = collection.get(include=[])["ids"]
    found_urls = set()

    print(f"Counting... (Total nodes found: {len(all_ids)})")

    batch_size = 5000
    for i in range(0, len(all_ids), batch_size):
        batch_ids = all_ids[i:i + batch_size]
        metas = collection.get(ids=batch_ids, include=["metadatas"])["metadatas"]
        for m in metas:
            if m and "url" in m:
                found_urls.add(m["url"])
        print(f"   Analyzed {min(i + batch_size, len(all_ids))}/{len(all_ids)} nodes...", end="\r")

    missing_urls = expected_urls - found_urls

    print(f"\n\nRESULT — {chroma_path}:")
    print("─" * 50)
    print(f"Total URLs in JSONL: {len(expected_urls)}")
    print(f"URLs found in index: {len(found_urls)}")
    print(f"MISSING URLs: {len(missing_urls)}")

    if missing_urls:
        log_file = f"missing_docs_{Path(chroma_path).name}.txt"
        print(f"\nFirst 10 missing URLs (written to {log_file}):")
        with open(log_file, "w") as f:
            for url in sorted(missing_urls):
                f.write(url + "\n")
        for url in list(missing_urls)[:10]:
            print(f" - {url}")
    print()


def final_audit():
    print(f"Reading source file: {JSONL_FILE}...")
    expected_urls = set()
    with open(JSONL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            if obj.get("url"):
                expected_urls.add(obj["url"])

    print(f"Expected URLs from file: {len(expected_urls)}\n")

    for path in CHROMA_PATHS:
        audit_index(path, expected_urls)


if __name__ == "__main__":
    final_audit()
