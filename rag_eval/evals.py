import os
import json
import asyncio
from pathlib import Path

import chromadb
from openai import OpenAI

from llama_index.core import VectorStoreIndex, Settings, StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai_like import OpenAILike
from llama_index.vector_stores.chroma import ChromaVectorStore

from ragas import Dataset, experiment

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ==============================================================================
# CONFIGURATION
# ==============================================================================

INDEX_DIR        = "rag_index"
SIMILARITY_TOP_K = 15
SCORE_THRESHOLDS = {"high": 0.7, "medium": 0.6}
CONTEXT_WINDOW   = 8192
MAX_TOKENS       = 1024

# ==============================================================================
# RAG SETUP
# ==============================================================================

Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-m3",
    embed_batch_size=4,
)

Settings.llm = OpenAILike(
    model="ggml-org/gpt-oss-120b-GGUF",
    api_base="http://172.30.42.129:8080/v1",
    api_key="not_necessary",
    context_window=CONTEXT_WINDOW,
    max_tokens=MAX_TOKENS,
    temperature=0.2,
    is_chat_model=True,
)


def load_index(persist_dir: str = INDEX_DIR) -> VectorStoreIndex:
    """Load the ChromaDB index from disk."""
    db = chromadb.PersistentClient(path=persist_dir)
    chroma_collection = db.get_or_create_collection("quickstart")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_context,
        embed_model=Settings.embed_model,
    )


def query_rag(index: VectorStoreIndex, question: str) -> dict:
    """
    Run a full RAG query: retrieve chunks + generate answer.

    Returns
    -------
    dict:
        answer   : str        — LLM-generated answer
        contexts : list[str]  — raw chunk texts (required by future RAGAS metrics)
        chunks   : list[dict] — full debug info per chunk
    """
    retriever = index.as_retriever(similarity_top_k=SIMILARITY_TOP_K)
    nodes = retriever.retrieve(question)

    contexts, chunks = [], []
    for rank, node_with_score in enumerate(nodes, start=1):
        score = node_with_score.score or 0.0
        node  = node_with_score.node
        text  = node.get_content()

        if score >= SCORE_THRESHOLDS["high"]:
            relevance = "HIGH"
        elif score >= SCORE_THRESHOLDS["medium"]:
            relevance = "MEDIUM"
        else:
            relevance = "LOW"

        contexts.append(text)
        chunks.append({
            "rank":      rank,
            "score":     round(score, 4),
            "relevance": relevance,
            "doc_type":  node.metadata.get("type", "unknown"),
            "preview":   text[:200].replace("\n", " "),
            "source":    node.metadata.get("url", "N/A"),
        })

    query_engine = index.as_query_engine(similarity_top_k=SIMILARITY_TOP_K)
    response = query_engine.query(question)

    return {
        "answer":   str(response.response),
        "contexts": contexts,
        "chunks":   chunks,
    }


# ==============================================================================
# JUDGE LLM
# Scores the RAG answer directly via OpenAI client with response_format
# json_object — bypasses instructor/response_model which the model does not support.
# ==============================================================================

judge_client = OpenAI(
    api_key="anything",
    base_url="http://localhost:4000/v1",
)

JUDGE_SYSTEM_PROMPT = (
    "You are a strict evaluator. "
    "You will receive a response, grading notes, and an expected answer. "
    "Think step by step, then on the LAST LINE output ONLY a JSON object "
    "with a single key 'result' whose value is 'pass' or 'fail'. "
    "Example last line: {\"result\": \"pass\"}"
)

JUDGE_USER_TEMPLATE = (
    "Response: {response}\n"
    "Grading Notes: {grading_notes}\n"
    "Expected Answer: {expected_answer}\n\n"
    'Return JSON: {{"result": "pass"}} or {{"result": "fail"}}'
)


def judge_score(response: str, grading_notes: str, expected_answer: str) -> str:
    """
    Call the judge LLM and return 'pass', 'fail', or 'error'.
    Extracts the verdict from the last line, allowing the model to reason freely.
    """
    prompt = JUDGE_USER_TEMPLATE.format(
        response=response,
        grading_notes=grading_notes,
        expected_answer=expected_answer,
    )
    try:
        completion = judge_client.chat.completions.create(
            model="ggml-org/gpt-oss-120b-GGUF",
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=512,  # enough space for reasoning + final JSON line
            temperature=0.0,
        )

        msg = completion.choices[0].message
        raw = msg.content or ""

        # This model returns the answer in reasoning_content when content is empty
        if not raw.strip():
            raw = getattr(msg, "reasoning_content", "") or ""

        print(f"Judge raw response: repr={repr(raw)}")

        # Extract last non-empty line — where the JSON verdict should be
        last_line = [l.strip() for l in raw.strip().splitlines() if l.strip()][-1]
        parsed = json.loads(last_line)

        value = parsed.get("result", "").strip().lower()
        return value if value in ("pass", "fail") else "error"

    except Exception as e:
        print(f"Judge error: {type(e).__name__}: {e}")
        return "error"


# ==============================================================================
# DATASET
# ==============================================================================

def load_dataset() -> Dataset:
    """
    Define the evaluation dataset.
    Fields:
        question       — query sent to the RAG
        grading_notes  — key points the answer must cover
        expected_answer— ground truth (used by future Answer Correctness metric)
    """
    dataset = Dataset(
        name="test_dataset",
        backend="local/csv",
        root_dir="evals",
    )

    samples = [
        {
            "question":        "dove si trova la sede dell'università di Trieste?",
            "grading_notes":   "deve menzionare Piazzale Europa e Trieste",
            "expected_answer": "Piazzale Europa 1, 34127 Trieste, Italia",
        },
        {
            "question":        "dove si può stampare all'università?",
            "grading_notes":   "deve menzionare dove è possibile stampare o chi contattare",
            "expected_answer": "Sì, è possibile stampare presso l'edificio H3",
        },
        {
            "question":        "a chi devo rivolgermi per info e chiarimenti su tasse?",
            "grading_notes":   "deve indicare un ufficio o contatto specifico per le tasse universitarie",
            "expected_answer": "Devi rivolgerti all'ufficio tasse o alla segreteria studenti",
        },
    ]

    for sample in samples:
        dataset.append(sample)

    dataset.save()
    return dataset


# ==============================================================================
# EXPERIMENT
# ==============================================================================

_index = load_index(INDEX_DIR)  # loaded once at module level, reused for every row


@experiment()
async def run_experiment(row: dict) -> dict:
    """
    For each dataset row:
      1. Query the RAG → answer + contexts + chunks
      2. Score the answer with the judge LLM (manual call, no instructor)
      3. Return the full result dict for CSV saving
    """

    try:
        rag_result = query_rag(_index, row["question"])

        score = judge_score(
            response=rag_result["answer"],
            grading_notes=row["grading_notes"],
            expected_answer=row.get("expected_answer", ""),
        )


        return {
            # dataset fields
            "question":        row["question"],
            "grading_notes":   row["grading_notes"],
            "expected_answer": row.get("expected_answer", ""),
            # RAG output
            "answer":          rag_result["answer"],
            "contexts":        " | ".join(rag_result["contexts"]),
            # evaluation
            "score":           score,
            # retrieval debug
            "top_chunk_score": rag_result["chunks"][0]["score"]  if rag_result["chunks"] else None,
            "top_chunk_src":   rag_result["chunks"][0]["source"] if rag_result["chunks"] else None,
        }
    except Exception as e:
        print(f"Judge error: {type(e).__name__}: {e}")
        print(f"Raw response was: repr={repr(raw)}")
        return "error"

# ==============================================================================
# ENTRY POINT
# ==============================================================================

async def main():
    dataset = load_dataset()
    print(f"Dataset loaded: {len(dataset)} samples")

    experiment_results = await run_experiment.arun(dataset)
    print("Experiment completed.")

    experiment_results.save()
    print(f"Results saved to: evals/experiments/{experiment_results.name}.csv")


if __name__ == "__main__":
    asyncio.run(main())