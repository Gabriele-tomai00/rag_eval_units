import json
import chromadb
from pathlib import Path

JSONL_FILE = "../md_results/cleaned_pages_big.jsonl"
CHROMA_PATHS = [
    "index_markdown_and_sentence_big_512",
    "index_sentence_big_512",
    "index_markdown_big_512",
]


def audit_index(chroma_path: str, expected_urls: set) -> None:
    if not Path(chroma_path).exists():
        print(f"⏭️  {chroma_path} — cartella non trovata, salto.\n")
        return

    print(f"📡 Connessione a ChromaDB in: {chroma_path}...")
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_collection("quickstart")

    all_ids = collection.get(include=[])["ids"]
    found_urls = set()

    print(f"Counting... (Nodi totali trovati: {len(all_ids)})")

    batch_size = 5000
    for i in range(0, len(all_ids), batch_size):
        batch_ids = all_ids[i:i + batch_size]
        metas = collection.get(ids=batch_ids, include=["metadatas"])["metadatas"]
        for m in metas:
            if m and "url" in m:
                found_urls.add(m["url"])
        print(f"   Analizzati {min(i + batch_size, len(all_ids))}/{len(all_ids)} nodi...", end="\r")

    missing_urls = expected_urls - found_urls

    print(f"\n\n📊 RISULTATO — {chroma_path}:")
    print("─" * 50)
    print(f"URL totali nel JSONL: {len(expected_urls)}")
    print(f"URL trovati nell'indice: {len(found_urls)}")
    print(f"URL MANCANTI: {len(missing_urls)}")

    if missing_urls:
        log_file = f"missing_docs_{Path(chroma_path).name}.txt"
        print(f"\n📝 Primi 10 URL mancanti (scritti in {log_file}):")
        with open(log_file, "w") as f:
            for url in sorted(missing_urls):
                f.write(url + "\n")
        for url in list(missing_urls)[:10]:
            print(f" - {url}")
    print()


def final_audit():
    print(f"📖 Lettura file sorgente: {JSONL_FILE}...")
    expected_urls = set()
    with open(JSONL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            if obj.get("url"):
                expected_urls.add(obj["url"])

    print(f"✅ URL attesi dal file: {len(expected_urls)}\n")

    for path in CHROMA_PATHS:
        audit_index(path, expected_urls)


if __name__ == "__main__":
    final_audit()