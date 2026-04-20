import os
import asyncio
import argparse
import time

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

async def main(type: int, big: bool, chunk_size: int) -> None:
    index_dirs = {
        1: ("index_sentence", "index_sentence_big"),
        2: ("index_markdown_chunking", "index_markdown_chunking_big"),
        3: ("index_markdown_and_sentence", "index_markdown_and_sentence_big"),
    }

    chunk_size_mapping = {
        128: 10,
        256: 20,
        512: 50,
        1024: 100,
    }

    chunk_overlap = chunk_size_mapping[chunk_size]

    docs = load_md_docs("../md_results/cleaned_pages_big.jsonl") if big else load_md_docs("../md_results/cleaned_pages.jsonl")
    if type != 2:
        index_dir = f"{index_dirs[type][1 if big else 0]}_{chunk_size}"
    else:
        index_dir = index_dirs[type][1 if big else 0]
        
    remove_index(index_dir)

    print("\n\n\n")
    print(f"Creating index with {index_dir}...")
    index = load_or_create_index(index_dir)
    if index is None:
        print("Failed to load or create the index.")
        return

    if type == 1:
        add_to_index_md_files_sentence_splitter(index, docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    elif type == 2:
        add_to_index_md_files_md_splitter(index, docs)
    elif type == 3:
        add_to_index_md_files_hybrid_md_and_text_splitter(index, docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        
    zip_file = zip_folder(index_dir)
    print(f"Index folder '{index_dir}' zipped to '{zip_file}'.")
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
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Program for the index creation phase")
    parser.add_argument(
        "--type", "-t",
        type=int,
        choices=[1, 2, 3],
        required=True,
        help="1 for sentence splitting, 2 for markdown structure splitting, 3 for hybrid markdown + sentence splitting",
    )   
    parser.add_argument(
        "--chunk_size", "-c",
        type=int,
        default=512,
        choices=[128, 256, 512, 1024],
        help="Size of the chunks (128, 256, 512, 1024). Overlap is derived automatically.",
    )   
    parser.add_argument(
        "--big", "-b",
        action="store_true",
        default=False,
        help="1 if you want to use thousands of documents (will create a bigger index, but may be more effective), 0 to use only a few dozens of documents (faster to create and query, but less effective)",
    )    
    args = parser.parse_args()

    asyncio.run(main(args.type, args.big, args.chunk_size))
    print(f"Time needed: {format_time(time.time() - start_time)}")