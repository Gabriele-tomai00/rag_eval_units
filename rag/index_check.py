import json
import chromadb
from pathlib import Path

# Configura i percorsi corretti
JSONL_FILE = "../md_results/cleaned_pages_big.jsonl"
CHROMA_PATH = "index_markdown_and_sentence_big_512"

def final_audit():
    # 1. Carichiamo tutti gli URL che DOVREBBERO esserci
    print(f"📖 Lettura file sorgente: {JSONL_FILE}...")
    expected_urls = set()
    with open(JSONL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            if obj.get("url"):
                expected_urls.add(obj["url"])
    
    print(f"✅ URL attesi dal file: {len(expected_urls)}")

    # 2. Leggiamo cosa c'è davvero dentro l'indice
    print(f"📡 Connessione a ChromaDB in: {CHROMA_PATH}...")
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection("quickstart")
    
    # Prendiamo tutti gli ID per iterare (evitiamo l'errore SQL variables)
    all_ids = collection.get(include=[])["ids"]
    found_urls = set()
    
    print(f"Counting... (Nodi totali trovati: {len(all_ids)})")
    
    batch_size = 5000
    for i in range(0, len(all_ids), batch_size):
        batch_ids = all_ids[i:i+batch_size]
        metas = collection.get(ids=batch_ids, include=["metadatas"])["metadatas"]
        for m in metas:
            if m and "url" in m:
                found_urls.add(m["url"])
        print(f"   Analizzati {min(i+batch_size, len(all_ids))}/{len(all_ids)} nodi...", end="\r")

    # 3. Confronto finale
    missing_urls = expected_urls - found_urls
    
    print(f"\n\n📊 RISULTATO FINALE:")
    print(f"─" * 30)
    print(f"URL totali nel JSONL: {len(expected_urls)}")
    print(f"URL trovati nell'indice: {len(found_urls)}")
    print(f"URL MANCANTI: {len(missing_urls)}")
    
    if missing_urls:
        print("\n📝 Primi 10 URL mancanti (scritti in missing_docs.txt):")
        with open("missing_docs.txt", "w") as f:
            for url in sorted(list(missing_urls)):
                f.write(url + "\n")
        for url in list(missing_urls)[:10]:
            print(f" - {url}")

if __name__ == "__main__":
    final_audit()