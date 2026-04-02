import os
import asyncio

from llama_index.core import Settings
from utils_rag import *

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ==============================================================================
# CORE QUERY FUNCTIONS
# ==============================================================================

def ask(index, question: str) -> str:
    """
    Query the RAG index and return only the LLM answer as a plain string.

    Parameters
    ----------
    index    : VectorStoreIndex
    question : str

    Returns
    -------
    str — the LLM-generated answer, nothing else.
    """
    query_engine = index.as_query_engine(similarity_top_k=SIMILARITY_TOP_K)
    response = query_engine.query(question)
    return str(response.response)


async def ask_debug(index, question: str) -> dict:
    """
    Query the RAG index and return the LLM answer together with retrieval
    details (chunks, scores, relevance labels, metadata).

    Parameters
    ----------
    index    : VectorStoreIndex
    question : str

    Returns
    -------
    dict with keys:
        answer   : str        — the LLM answer
        question : str        — the original question
        chunks   : list[dict] — retrieved nodes with score/relevance/preview/metadata
    """
    # --- retrieval ---------------------------------------------------------
    retriever = index.as_retriever(similarity_top_k=SIMILARITY_TOP_K)
    nodes = await retriever.aretrieve(question)

    chunks = []
    for rank, node_with_score in enumerate(nodes, start=1):
        score = node_with_score.score or 0.0
        node = node_with_score.node

        if score >= SCORE_THRESHOLDS["high"]:
            relevance = "HIGH"
        elif score >= SCORE_THRESHOLDS["medium"]:
            relevance = "MEDIUM"
        else:
            relevance = "LOW"

        chunks.append({
            "rank":     rank,
            "score":    round(score, 4),
            "relevance": relevance,
            "doc_type": node.metadata.get("type", "unknown"),
            "preview":  node.get_content()[:200].replace("\n", " "),
            "metadata": node.metadata,
        })

    # --- generation --------------------------------------------------------
    query_engine = index.as_query_engine(similarity_top_k=SIMILARITY_TOP_K)
    response = query_engine.query(question)

    return {
        "question": question,
        "answer":   str(response.response),
        "chunks":   chunks,
    }


def print_debug_result(result: dict) -> None:
    """Pretty-print the output of ask_debug()."""
    bar = "─" * 70
    print(f"\n{'═'*70}")
    print(f"  QUERY : {result['question']}")
    print(f"{'═'*70}")
    print(f"  Retrieved {len(result['chunks'])} chunk(s)  "
          f"[HIGH ≥ {SCORE_THRESHOLDS['high']},"
          f" MEDIUM ≥ {SCORE_THRESHOLDS['medium']}]")
    print(bar)

    for c in result["chunks"]:
        print(f"  #{c['rank']}  score={c['score']:.4f}  [{c['relevance']:<6}]  type={c['doc_type']}")
        print(f"       preview : {c['preview'][:120]}...")
        print(f"       source  : {c['metadata'].get('url', 'N/A')}")
        print(bar)

    scores = [c["score"] for c in result["chunks"]]
    if scores:
        high_count = sum(1 for c in result["chunks"] if c["relevance"] == "HIGH")
        print(f"  ▸ best={max(scores):.4f}  avg={sum(scores)/len(scores):.4f}  worst={min(scores):.4f}")
        print(f"  ▸ HIGH relevance: {high_count}/{len(result['chunks'])}")

    print(f"\n  LLM ANSWER:\n  {result['answer']}")
    print("═" * 70)


# ==============================================================================
# ENTRY POINT
# ==============================================================================

async def main():

    INDEX_DIR_CHUNKING_SENTENCE = "rag_index_sentence_splitting"
    INDEX_DIR_CHUNKING_MD = "rag_index_markdown_chunking"
    INDEX_DIR_CHUNKING_MD_AND_SENTENCE = "rag_index_markdown_and_sentence_chunking"
    chunk_size=1000
    chunk_overlap=50   
    docs = load_md_docs("../md_results/cleaned_pages.jsonl")

    remove_index(INDEX_DIR_CHUNKING_SENTENCE)
    remove_index(INDEX_DIR_CHUNKING_MD)
    remove_index(INDEX_DIR_CHUNKING_MD_AND_SENTENCE)
    print("\n\n\n")

# INDEX_DIR_CHUNKING_SENTENCE
    print(f"Creating index with sentence splitting...")
    index = load_or_create_index(INDEX_DIR_CHUNKING_SENTENCE)
    if index is None:
        print("Failed to load or create the index.")
        return
    add_to_index_md_files_sentence_splitter(index, docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    print("\n\n\n")


# INDEX_DIR_CHUNKING_MD
    print(f"Creating index with markdown structure splitting...")
    index = load_or_create_index(INDEX_DIR_CHUNKING_MD)
    if index is None:
        print("Failed to load or create the index.")
        return
    add_to_index_md_files_md_splitter(index, docs)
    print("\n\n\n")

# INDEX_DIR_CHUNKING_MD_AND_SENTENCE
    print(f"Creating index with hybrid markdown + sentence splitting...")
    index = load_or_create_index(INDEX_DIR_CHUNKING_MD_AND_SENTENCE)
    if index is None:
        print("Failed to load or create the index.")
        return
    add_to_index_md_files_hybrid_md_and_text_splitter(index, docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    print("\n\n\n")

    
    # --- clean answer (no debug info) --------------------------------------
    # print("ANSWARE: Tell me about the Climbing for Climate (CFC) initiative\n")
    # answer = ask(index, "Tell me about the Climbing for Climate (CFC) initiative")
    # print(answer)
    # print("\n\n\n")


    # print("ANSWARE: a chi devo rivolgermi per info e chiarimenti su tasse\n")
    # answer = ask(index, "a chi devo rivolgermi per info e chiarimenti su tasse")
    # print(answer)
    # print("\n\n\n")

    # print("ANSWARE: dove si trova la sede dell'università di Trieste?\n")
    # answer = ask(index, "dove si trova la sede dell'università di Trieste?")
    # print(answer)
    # print("\n\n\n")

    # # --- answer with full debug info ---------------------------------------
    # print("ANSWARE: dove si trova la sede dell'università di Trieste?\n")
    # result = await ask_debug(index, "a chi devo rivolgermi per info e chiarimenti su tasse")
    # print_debug_result(result)


if __name__ == "__main__":
    asyncio.run(main())