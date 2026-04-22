import json
import hashlib
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
INSERT_BATCH_SIZE = 300  # nodes per ChromaDB commit (tunable independently from embed_batch_size)
load_dotenv()


def get_prompt_from_file(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-m3",
    embed_batch_size=96,  # safe upper limit for 512-token chunks on 15GB GPU
)

Settings.llm = OpenAILike(
    model=os.getenv("MODEL"),
    api_base=os.getenv("LLM_API_BASE"),
    api_key=os.getenv("API_KEY"),
    context_window=os.getenv("CONTEXT_WINDOW"),
    max_tokens=os.getenv("MAX_TOKENS"),
    temperature=os.getenv("TEMPERATURE"),
    is_chat_model=True,
    system_prompt=get_prompt_from_file("prompt_for_llm.txt"),
)

# ==============================================================================
# INDEX MANAGEMENT
# ==============================================================================

def load_or_create_index(index_dir: str) -> VectorStoreIndex:
    """Load an existing ChromaDB index or create a new empty one."""
    db = chromadb.PersistentClient(path=index_dir)
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


def load_md_docs(jsonl_path: str) -> list[Document]:
    """Load markdown documents from a JSONL file and return a list of Document objects."""
    path = Path(jsonl_path)
    if not path.exists():
        print(f"File not found: {jsonl_path}")
        return []

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
                text_template="INFO DOCUMENTO: {metadata_str}\n\nCONTENUTO:\n{content}",
                metadata_template="TITOLO: {value}",
                excluded_embed_metadata_keys=["url", "type"],
                excluded_llm_metadata_keys=["url", "type"]
            ))
    print(f"Loaded {len(docs)} documents from {jsonl_path}.")
    return docs


def _make_deterministic_ids(nodes: list) -> None:
    """
    Assign a stable, content-based ID to each node.
    Includes the node position to handle duplicate content across chunks.
    """
    for i, node in enumerate(nodes):
        content_hash = hashlib.sha256(
            f"{i}:{node.get_content()}".encode()
        ).hexdigest()[:32]
        node.id_ = content_hash


def _insert_nodes_incremental(index: VectorStoreIndex, nodes: list, label: str, resume: bool) -> None:
    """
    Insert nodes into the index in batches of INSERT_BATCH_SIZE.

    If resume=True, fetches existing node IDs from ChromaDB (no embeddings loaded,
    just string IDs from SQLite) and skips nodes that are already present.
    Node IDs must be deterministic (set via _make_deterministic_ids) for this to work.

    Parameters
    ----------
    index  : VectorStoreIndex
    nodes  : list of BaseNode
    label  : short string shown in progress output (e.g. "sentence", "hybrid")
    resume : if True, skip nodes whose ID is already in ChromaDB
    """
    if resume:
        # Retrieve only IDs from SQLite — zero GPU/embedding work involved
        existing_ids = set(index.vector_store._collection.get(include=[])["ids"])
        nodes_to_insert = [n for n in nodes if n.node_id not in existing_ids]
        print(f"  [{label}] resume mode: {len(existing_ids)} already committed, "
              f"{len(nodes_to_insert)} remaining")
    else:
        nodes_to_insert = nodes

    if not nodes_to_insert:
        print(f"  [{label}] nothing to insert, index is already complete")
        return

    total = len(nodes_to_insert)
    for start in range(0, total, INSERT_BATCH_SIZE):
        batch = nodes_to_insert[start:start + INSERT_BATCH_SIZE]
        index.insert_nodes(batch)
        committed = min(start + INSERT_BATCH_SIZE, total)
        print(f"  [{label}] committed {committed}/{total} nodes → SQLite flushed")


def add_to_index_md_files_sentence_splitter(index: VectorStoreIndex, docs: list[Document], chunk_size, chunk_overlap, resume: bool = False) -> None:
    text_splitter = SentenceSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    nodes = text_splitter.get_nodes_from_documents(docs)
    _make_deterministic_ids(nodes)

    chunk_lengths = [len(node.get_content().split()) for node in nodes]
    max_chunk_len = max(chunk_lengths) if chunk_lengths else 0
    print(f"Splitting done: {len(nodes)} nodes — longest chunk: {max_chunk_len} tokens (approx.)")

    _insert_nodes_incremental(index, nodes, label="sentence", resume=resume)


def add_to_index_md_files_md_splitter(index: VectorStoreIndex, docs: list[Document], resume: bool = False) -> None:
    md_parser = MarkdownNodeParser()
    nodes = md_parser.get_nodes_from_documents(docs)
    _make_deterministic_ids(nodes)

    chunk_lengths = [len(node.get_content().split()) for node in nodes]
    max_chunk_len = max(chunk_lengths) if chunk_lengths else 0
    print(f"Splitting done: {len(nodes)} nodes — longest chunk: {max_chunk_len} tokens (approx.)")

    _insert_nodes_incremental(index, nodes, label="markdown", resume=resume)


def add_to_index_md_files_hybrid_md_and_text_splitter(index: VectorStoreIndex, docs: list[Document], chunk_size, chunk_overlap, resume: bool = False) -> None:
    md_parser = MarkdownNodeParser()
    initial_nodes = md_parser.get_nodes_from_documents(docs)
    text_splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    final_nodes = text_splitter.get_nodes_from_documents(initial_nodes)
    _make_deterministic_ids(final_nodes)

    chunk_lengths = [len(node.get_content().split()) for node in final_nodes]
    max_chunk_len = max(chunk_lengths) if chunk_lengths else 0
    print(f"Splitting done: {len(final_nodes)} nodes — longest chunk: {max_chunk_len} tokens (approx.)")

    _insert_nodes_incremental(index, final_nodes, label="hybrid", resume=resume)




def remove_index(index_dir: str):
    if os.path.exists(index_dir):
        shutil.rmtree(index_dir)
        print(f"Deleted: {index_dir}")
    else:
        print(f"Directory not found: {index_dir}")


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


def zip_folder(folder_path: str) -> str:
    folder = Path(folder_path).resolve()

    if not folder.is_dir():
        raise ValueError(f"{folder} is not a valid directory")

    zip_path = folder.with_suffix('')

    # Create zip archive
    archive_path = shutil.make_archive(
        base_name=str(zip_path),
        format='zip',
        root_dir=str(folder.parent),
        base_dir=folder.name
    )

    return archive_path


def format_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = round(seconds % 60)
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"