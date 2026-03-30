import json
from datetime import datetime
from pathlib import Path
import chromadb
import shutil
import os
from dotenv import load_dotenv

from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai_like import OpenAILike
from llama_index.core import VectorStoreIndex, Settings, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.schema import Document
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter

# ==============================================================================
# CONFIGURATION
# ==============================================================================

INDEX_DIR = "rag_index"
SIMILARITY_TOP_K = 7
SCORE_THRESHOLDS = {"high": 0.7, "medium": 0.6}
load_dotenv()



def get_prompt_from_file(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-m3",
    embed_batch_size=4,
)

Settings.llm = OpenAILike(
    model=os.getenv("MODEL"),
    api_base=os.getenv("LLM_API_BASE"),
    api_key="not_necessary",
    context_window=os.getenv("CONTEXT_WINDOW"),
    max_tokens=os.getenv("MAX_TOKENS"),
    temperature=os.getenv("TEMPERATURE"),
    is_chat_model=True, # for using the new /v1/chat/completions API: role: system (for pr)
    system_prompt=get_prompt_from_file("prompt_for_llm.txt"),

)

# ==============================================================================
# INDEX MANAGEMENT
# ==============================================================================

def load_or_create_index() -> VectorStoreIndex:
    """Load an existing ChromaDB index or create a new empty one."""
    db = chromadb.PersistentClient(path=INDEX_DIR)
    chroma_collection = db.get_or_create_collection("quickstart")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_context,
        embed_model=Settings.embed_model,
    )


def get_index_size(index: VectorStoreIndex) -> int:
    """Return the number of documents currently stored in the index."""
    return index.vector_store._collection.count()


def add_to_index_md_files(index: VectorStoreIndex, jsonl_path: str) -> int:
    """
    Parse a JSONL file of markdown documents and insert them into the index.
    Uses a chained approach: Markdown structure + Sentence splitting for long texts.
    """
    path = Path(jsonl_path)
    if not path.exists():
        print(f"File not found: {jsonl_path}")
        return 0

    docs = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            content = data.get("content")
            url = data.get("url")
            title = data.get("title")
            if not content:
                continue
            docs.append(Document(
                text=content,
                metadata={
                    "url": url, 
                    "type": "markdown", 
                    "title": title
                },
                # Usiamo 'metadata_str' che è una chiave protetta di LlamaIndex, 
                # così non avrai mai più KeyError.
                text_template="INFO DOCUMENTO: {metadata_str}\n\nCONTENUTO:\n{content}",
                # Definiamo cosa deve apparire in 'metadata_str'
                metadata_template="TITOLO: {value}", 
                # Escludiamo url e type così in 'metadata_str' resta solo il titolo
                excluded_embed_metadata_keys=["url", "type"],
                excluded_llm_metadata_keys=["url", "type"]
            ))

    md_parser = MarkdownNodeParser()
    # Il SentenceSplitter serve a spezzare i nodi troppo lunghi.
    # Con un LLM da 120B, 1024 è un buon compromesso tra contesto e precisione.
    text_splitter = SentenceSplitter(chunk_size=1024, chunk_overlap=100)

    # 2. Eseguiamo il parsing a cascata (Chaining)
    # Prima dividiamo per struttura markdown
    initial_nodes = md_parser.get_nodes_from_documents(docs)
    
    # Poi passiamo i nodi al text_splitter per gestire i testi troppo densi
    final_nodes = text_splitter.get_nodes_from_documents(initial_nodes)

    index.insert_nodes(final_nodes)
    
    print(f"Inserted {len(final_nodes)} nodes from {jsonl_path} (after Markdown + Sentence splitting).")
    return len(final_nodes)


def remove_index():
    if os.path.exists(INDEX_DIR):
        shutil.rmtree(INDEX_DIR)
        print(f"Deleted: {INDEX_DIR}")
    else:
        print(f"Directory not found: {INDEX_DIR}")


# ==============================================================================
# UTILITY
# ==============================================================================

def _format_time(seconds: float) -> str:
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def print_indexing_summary(
    start_time: datetime,
    persist_dir: str,
    num_docs: int,
    log_file: str = "indexing_summary.log",
) -> None:
    elapsed = (datetime.now() - start_time).total_seconds()
    lines = [
        f"\n====== INDEX CREATION SESSION {start_time.strftime('%d-%m-%Y %H:%M')} ======",
        f"Time taken      : {_format_time(elapsed)}",
        f"Persist dir     : {persist_dir}",
        f"Documents added : {num_docs}",
        f"End time        : {datetime.now().strftime('%H:%M:%S')}",
        "=" * 55,
    ]
    for line in lines:
        print(line)
    with Path(log_file).open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")