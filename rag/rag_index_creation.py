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

    remove_index()
    
    index = load_or_create_index()
    if index is None:
        print("Failed to load or create the index.")
        return
    print(f"Index loaded. Size: {get_index_size(index)} documents.")
    print("\n\n\n")


    add_to_index_md_files(index, "../md_results/cleaned_pages.jsonl")

    
    # --- clean answer (no debug info) --------------------------------------
    # print("ANSWARE: Tell me about the Climbing for Climate (CFC) initiative\n")
    # answer = ask(index, "Tell me about the Climbing for Climate (CFC) initiative")
    # print(answer)
    # print("\n\n\n")


    # print("ANSWARE: a chi devo rivolgermi per info e chiarimenti su tasse\n")
    # answer = ask(index, "a chi devo rivolgermi per info e chiarimenti su tasse")
    # print(answer)
    # print("\n\n\n")

    print("ANSWARE: dove si trova la sede dell'università di Trieste?\n")
    answer = ask(index, "dove si trova la sede dell'università di Trieste?")
    print(answer)
    print("\n\n\n")

    # # --- answer with full debug info ---------------------------------------
    # print("ANSWARE: dove si trova la sede dell'università di Trieste?\n")
    # result = await ask_debug(index, "a chi devo rivolgermi per info e chiarimenti su tasse")
    # print_debug_result(result)


if __name__ == "__main__":
    asyncio.run(main())