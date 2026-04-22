import json
import hashlib
import shutil
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import chromadb
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
INSERT_BATCH_SIZE = 500  # nodes per ChromaDB commit (tunable independently from embed_batch_size)
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
# SQLITE RECOVERY
# ==============================================================================

def _check_integrity(db_path: str) -> tuple[bool, list[str]]:
    """Run PRAGMA integrity_check. Returns (is_ok, list_of_issues)."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    results = [row[0] for row in conn.execute("PRAGMA integrity_check").fetchall()]
    conn.close()
    return results == ["ok"], results


def _rebuild_fts5(db_path: str) -> bool:
    """Rebuild the FTS5 inverted index for embedding_fulltext_search."""
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO embedding_fulltext_search(embedding_fulltext_search) VALUES('rebuild')"
        )
        conn.commit()
        conn.close()
        print("  [OK] FTS5 index rebuilt.")
        return True
    except Exception as e:
        print(f"  [WARN] FTS5 rebuild failed: {e}")
        return False


def _recover_table_indexed(src, dst, table: str, cols: list[str]) -> tuple[int, int]:
    """Standard recovery: list rowids via btree, then fetch each row individually."""
    placeholders = ",".join(["?"] * len(cols))
    rowids = [r[0] for r in src.execute(f"SELECT rowid FROM '{table}' ORDER BY rowid").fetchall()]
    ok, skip = 0, 0
    for rowid in rowids:
        try:
            data = src.execute(
                f"SELECT {','.join(cols)} FROM '{table}' WHERE rowid=?", (rowid,)
            ).fetchone()
            if data:
                dst.execute(
                    f"INSERT OR IGNORE INTO '{table}' ({','.join(cols)}) VALUES ({placeholders})",
                    data,
                )
                ok += 1
        except Exception:
            skip += 1
    dst.commit()
    return ok, skip


def _recover_table_bruteforce(
    src, dst, table: str, cols: list[str], max_rowid: int
) -> tuple[int, int]:
    """
    Fallback for tables where the btree is too corrupted to list rowids.
    Scans every integer rowid from 1 to max_rowid sequentially.
    Stops early after MAX_CONSECUTIVE_MISS consecutive empty slots.
    """
    placeholders = ",".join(["?"] * len(cols))
    MAX_CONSECUTIVE_MISS = 50_000
    ok, skip, consecutive_miss = 0, 0, 0

    print(f"    Bruteforce scan up to rowid {max_rowid} ...", flush=True)
    for rowid in range(1, max_rowid + 1):
        try:
            data = src.execute(
                f"SELECT {','.join(cols)} FROM '{table}' WHERE rowid=?", (rowid,)
            ).fetchone()
            if data:
                dst.execute(
                    f"INSERT OR IGNORE INTO '{table}' ({','.join(cols)}) VALUES ({placeholders})",
                    data,
                )
                ok += 1
                consecutive_miss = 0
                if ok % 10_000 == 0:
                    dst.commit()
                    print(f"    ... {ok} rows so far (rowid {rowid})", flush=True)
            else:
                consecutive_miss += 1
        except Exception:
            skip += 1
            consecutive_miss += 1

        if consecutive_miss >= MAX_CONSECUTIVE_MISS:
            print(f"    Early stop: {MAX_CONSECUTIVE_MISS} consecutive empty rowids at {rowid}.")
            break

    dst.commit()
    return ok, skip


def _recover_db(source_path: str, dest_path: str, bruteforce_max_rowid: int) -> bool:
    """
    Full row-by-row recovery of a corrupted SQLite file.
    FTS5 virtual tables are skipped during copy and reconstructed at the end.
    """
    print(f"  Starting recovery: {source_path} -> {dest_path}")

    src = sqlite3.connect(source_path)
    src.execute("PRAGMA journal_mode=OFF")
    src.execute("PRAGMA synchronous=OFF")

    dst = sqlite3.connect(dest_path)
    dst.execute("PRAGMA journal_mode=WAL")
    dst.execute("PRAGMA synchronous=NORMAL")
    dst.execute("PRAGMA cache_size=-65536")  # 256 MB cache

    # FTS5 virtual tables — skip during row copy, rebuild from schema at the end
    FTS5_TABLES = {
        "embedding_fulltext_search",
        "embedding_fulltext_search_config",
        "embedding_fulltext_search_content",
        "embedding_fulltext_search_data",
        "embedding_fulltext_search_docsize",
        "embedding_fulltext_search_idx",
    }

    try:
        all_objects = src.execute(
            "SELECT type, name, sql FROM sqlite_master ORDER BY name"
        ).fetchall()
    except Exception as e:
        print(f"  [ERROR] Cannot read schema: {e}")
        src.close(); dst.close()
        return False

    # Recreate schema on destination (tables + indexes, skip FTS5)
    for obj_type, name, sql in all_objects:
        if sql is None or name in FTS5_TABLES:
            continue
        try:
            dst.execute(sql)
        except Exception:
            pass
    dst.commit()

    tables = [
        name for obj_type, name, sql in all_objects
        if obj_type == "table" and name not in FTS5_TABLES and sql is not None
    ]
    print(f"  Tables to recover: {tables}\n")

    total_ok, total_skip = 0, 0
    for table in tables:
        cols = [r[1] for r in src.execute(f"PRAGMA table_info('{table}')").fetchall()]
        if not cols:
            print(f"  Table '{table}': no columns, skipping.")
            continue

        print(f"  Table '{table}' ...", end=" ", flush=True)
        try:
            ok, skip = _recover_table_indexed(src, dst, table, cols)
            method = "indexed"
        except Exception as e:
            print(f"\n    [WARN] Indexed scan failed ({e}), switching to bruteforce ...")
            ok, skip = _recover_table_bruteforce(src, dst, table, cols, bruteforce_max_rowid)
            method = "bruteforce"

        print(f"{ok} rows recovered, {skip} skipped [{method}]")
        total_ok += ok
        total_skip += skip

    # Recreate FTS5 virtual table from original schema
    for obj_type, name, sql in all_objects:
        if name == "embedding_fulltext_search" and sql:
            try:
                dst.execute(sql)
                dst.commit()
                print(f"  FTS5 virtual table '{name}' recreated.")
            except Exception as e:
                print(f"  [WARN] FTS5 table creation: {e}")
            break

    src.close()
    dst.close()
    print(f"\n  Recovery done: {total_ok} rows recovered, {total_skip} skipped.")
    return True


def ensure_healthy_chroma_db(chroma_dir: str, bruteforce_max_rowid: int = 600_000) -> bool:
    """
    Check the integrity of chroma.sqlite3 inside chroma_dir and repair it if needed.

    Repair strategy (in order of severity):
      1. Database is healthy          → do nothing
      2. Only FTS5 index corrupted    → fast in-place rebuild (~1 s)
      3. Structural corruption        → full row-by-row recovery, then FTS5 rebuild

    A backup is created at chroma.sqlite3.backup before any destructive operation.
    The repaired file replaces the original in-place so the rest of the codebase
    does not need to change any paths.

    Parameters
    ----------
    chroma_dir          : folder that contains chroma.sqlite3
    bruteforce_max_rowid: upper bound for sequential rowid scan on corrupted tables.
                         Set it slightly above the expected number of rows in the
                         largest table (default 600_000 covers most cases).

    Returns
    -------
    True if the database is healthy (or was successfully repaired), False otherwise.
    """
    db_path = os.path.join(chroma_dir, "chroma.sqlite3")
    backup_path = db_path + ".backup"
    recovered_path = db_path + ".recovered"

    if not os.path.exists(db_path):
        # No DB yet — nothing to check, ChromaDB will create it fresh
        return True

    print(f"[DB CHECK] Verifying integrity: {db_path}")
    is_ok, issues = _check_integrity(db_path)

    if is_ok:
        print("[DB CHECK] OK — database is healthy.")
        return True

    non_fts_issues = [i for i in issues if "fts" not in i.lower() and "FTS5" not in i]

    if not non_fts_issues:
        # Only FTS5 corruption — fast in-place fix
        print("[DB CHECK] Only FTS5 index corrupted — rebuilding in-place ...")
        _rebuild_fts5(db_path)
        is_ok, _ = _check_integrity(db_path)
        if is_ok:
            print("[DB CHECK] Fixed — database is now healthy.")
            return True

    # Structural corruption — full recovery
    print(f"[DB CHECK] Structural corruption detected ({len(issues)} issue(s)) — starting recovery ...")

    if not os.path.exists(backup_path):
        print(f"  Creating backup: {backup_path}")
        shutil.copy2(db_path, backup_path)

    if os.path.exists(recovered_path):
        os.remove(recovered_path)

    if not _recover_db(db_path, recovered_path, bruteforce_max_rowid):
        print("[DB CHECK] Recovery failed — aborting.")
        return False

    print("[DB CHECK] Rebuilding FTS5 on recovered database ...")
    _rebuild_fts5(recovered_path)

    is_ok, remaining = _check_integrity(recovered_path)
    if not is_ok:
        print(f"[DB CHECK] Recovered DB still has issues: {remaining[:5]}")
        return False

    os.replace(recovered_path, db_path)
    print(f"[DB CHECK] Recovery complete. Backup kept at: {backup_path}")
    return True


# ==============================================================================
# INDEX MANAGEMENT
# ==============================================================================

def load_or_create_index(index_dir: str, bruteforce_max_rowid: int = 600_000) -> VectorStoreIndex | None:
    """
    Load an existing ChromaDB index or create a new empty one.
    Always checks and repairs chroma.sqlite3 before opening the database.

    Parameters
    ----------
    index_dir            : folder containing (or that will contain) the ChromaDB files
    bruteforce_max_rowid : passed to ensure_healthy_chroma_db for corrupted table scans
    """
    # Always verify and repair the SQLite file before handing it to ChromaDB
    if not ensure_healthy_chroma_db(index_dir, bruteforce_max_rowid):
        print(f"[ERROR] Database at '{index_dir}' could not be recovered.")
        return None

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
    for i, node in enumerate(nodes):
        url = node.metadata.get("url", "")
        content_hash = hashlib.sha256(
            f"{i}:{url}:{node.get_content()}".encode()
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


def add_to_index_md_files_sentence_splitter(
    index: VectorStoreIndex, docs: list[Document], chunk_size, chunk_overlap, resume: bool = False
) -> None:
    text_splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    nodes = text_splitter.get_nodes_from_documents(docs)
    _make_deterministic_ids(nodes)

    chunk_lengths = [len(node.get_content().split()) for node in nodes]
    max_chunk_len = max(chunk_lengths) if chunk_lengths else 0
    print(f"Splitting done: {len(nodes)} nodes — longest chunk: {max_chunk_len} tokens (approx.)")

    _insert_nodes_incremental(index, nodes, label="sentence", resume=resume)


def add_to_index_md_files_md_splitter(
    index: VectorStoreIndex, docs: list[Document], resume: bool = False
) -> None:
    md_parser = MarkdownNodeParser()
    nodes = md_parser.get_nodes_from_documents(docs)
    _make_deterministic_ids(nodes)

    chunk_lengths = [len(node.get_content().split()) for node in nodes]
    max_chunk_len = max(chunk_lengths) if chunk_lengths else 0
    print(f"Splitting done: {len(nodes)} nodes — longest chunk: {max_chunk_len} tokens (approx.)")

    _insert_nodes_incremental(index, nodes, label="markdown", resume=resume)


def add_to_index_md_files_hybrid_md_and_text_splitter(
    index: VectorStoreIndex, docs: list[Document], chunk_size, chunk_overlap, resume: bool = False
) -> None:
    md_parser = MarkdownNodeParser()
    initial_nodes = md_parser.get_nodes_from_documents(docs)
    text_splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    final_nodes = text_splitter.get_nodes_from_documents(initial_nodes)
    _make_deterministic_ids(final_nodes)

    chunk_lengths = [len(node.get_content().split()) for node in final_nodes]
    max_chunk_len = max(chunk_lengths) if chunk_lengths else 0
    print(f"Splitting done: {len(final_nodes)} nodes — longest chunk: {max_chunk_len} tokens (approx.)")

    _insert_nodes_incremental(index, final_nodes, label="hybrid", resume=resume)


def remove_index(index_dir: str) -> None:
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
    archive_path = shutil.make_archive(
        base_name=str(folder.with_suffix("")),
        format="zip",
        root_dir=str(folder.parent),
        base_dir=folder.name,
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