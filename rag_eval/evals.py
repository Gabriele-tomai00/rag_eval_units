import os
import asyncio
from dotenv import load_dotenv
import re
import argparse

from questions_answares import samples

import chromadb
from openai import OpenAI

from llama_index.core import VectorStoreIndex, Settings, StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai_like import OpenAILike
from llama_index.vector_stores.chroma import ChromaVectorStore

from ragas import Dataset, experiment
from ragas.run_config import RunConfig

# Faithfulness
from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.run_config import RunConfig

# RAGAS metrics
from ragas.metrics.collections import (
    Faithfulness,
    AnswerCorrectness,
    AnswerRelevancy,
    ContextPrecisionWithReference,
    ContextRecall,
)

from ragas.embeddings import HuggingFaceEmbeddings as RagasHFEmbeddings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HUGGINGFACE_HUB_VERBOSITY"] = "error"

load_dotenv()


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

# ==============================================================================
# ARGUMENT PARSING
# ==============================================================================

def parse_args():
    parser = argparse.ArgumentParser(description="RAG evaluation script using RAGAS framework")
    parser.add_argument(
        "--type", "-t",
        type=int,
        choices=[1, 2, 3],
        required=True,
        help="1 for sentence splitting, 2 for markdown structure splitting, 3 for hybrid markdown + sentence splitting",
    )
    parser.add_argument(
        "--big", "-b",
        action="store_true",
        default=False,
        help="Use the larger index (thousands of documents). Omit for the smaller index (dozens of documents).",
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        default=False,
        help="Enable all metrics (may be slow).",
    )
    parser.add_argument(
        "--top_k", "-k",
        type=int,
        default=5,
        help="The number of top k chunks retireved",
    )
    parser.add_argument(
        "--chunk_size", "-c",
        type=int,
        choices=[128, 256, 512, 1024],
        default=512,
        help="Chunk size used when building the index (128, 256, 512, 1024). Default: 512.",
    )
    return parser.parse_args()


def resolve_index_config(args) -> tuple[str, str]:
    """
    Map CLI arguments to (INDEX_DIR, OUTPUT_FILENAME).

    index_type:
        1 → sentence splitting
        2 → markdown chunking
        3 → markdown + sentence (hybrid)
    big:
        False → standard index
        True  → big index
    """
    big = args.big
    index_type = args.type
    top_k = args.top_k
    chunk_size = args.chunk_size

    suffix = "_big" if big else ""

    mapping = {
        1: ("index_sentence",              "from_index_sentence"),
        2: ("index_markdown_chunking",     "from_index_markdown_chunking"),
        3: ("index_markdown_and_sentence", "from_index_markdown_and_sentence"),
    }

    folder, name = mapping[index_type]
    chunk_suffix = "" if index_type == 2 else f"_{chunk_size}"
    index_dir       = f"../rag/{folder}{suffix}{chunk_suffix}"
    output_filename = f"{name}{suffix}{chunk_suffix}_k_{top_k}_results"

    return index_dir, output_filename

# ==============================================================================
# CONFIGURATION
# ==============================================================================

_args = parse_args()
INDEX_DIR, OUTPUT_FILENAME = resolve_index_config(_args)

SIMILARITY_TOP_K  = _args.top_k
print("SIMILARITY_TOP_K: ", SIMILARITY_TOP_K)
# SIMILARITY_CUTOFF = 0.35
SCORE_THRESHOLDS  = {"high": 0.7, "medium": 0.6}

# Feature flags — disable expensive metrics during quick debug runs
if _args.all:
    ENABLE_JUDGE                    = True
    ENABLE_FAITHFULNESS             = True
    ENABLE_ANSWER_CORRECTNESS       = True
    ENABLE_RESPONSE_RELEVANCY       = True
    ENABLE_CONTEXT_PRECISION        = True
    ENABLE_CONTEXT_RECALL           = True
else:
    ENABLE_JUDGE                    = True
    ENABLE_FAITHFULNESS             = False
    ENABLE_ANSWER_CORRECTNESS       = True
    ENABLE_RESPONSE_RELEVANCY       = False
    ENABLE_CONTEXT_PRECISION        = False
    ENABLE_CONTEXT_RECALL           = False


# Conservative config for a local/unstable vLLM service
_run_config = RunConfig(
    max_workers=28,
    timeout=600,
    max_retries=4,
)

# ==============================================================================
# RAG SETUP
# ==============================================================================

Settings.embed_model = HuggingFaceEmbedding(
    model_name=os.getenv("EMBEDDING_MODEL"),
    embed_batch_size=4,
)

Settings.llm = OpenAILike(
    model=os.getenv("MODEL"),
    api_base=os.getenv("LLM_API_BASE"),
    api_key=os.getenv("API_KEY"),
    context_window=int(os.getenv("CONTEXT_WINDOW")),
    max_tokens=int(os.getenv("MAX_TOKENS")),
    temperature=float(os.getenv("TEMPERATURE")),
    is_chat_model=True,
    system_prompt=(
            "Sei l'assistente virtuale dell'università degli studi di Trieste "
            "Rispondi SEMPRE in italiano, anche se i documenti forniti sono in una lingua diversa. "
            "Se non conosci la risposta, ammettilo chiaramente senza inventare informazioni. "
            "Usa solo le informazioni fornite nei contesti, non fare supposizioni o aggiunte. "
            "Devi essere conciso e preciso, non dilungarti in spiegazioni non richieste. "
        ),
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
    Esegue una query RAG completa: recupera i chunk, applica il filtro di similarità
    e genera una risposta coerente.
    """
    # 1. Configurazione del Query Engine con Post-Processor
    query_engine = index.as_query_engine(
        similarity_top_k=SIMILARITY_TOP_K,
        # node_postprocessors=[
        #     SimilarityPostprocessor(similarity_cutoff=SIMILARITY_CUTOFF)
        # ]
    )
    
    response = query_engine.query(question)
    
    # for "Empty Response"
    final_answer = str(response.response).strip()
    
    is_empty = (
        not final_answer or 
        final_answer.lower() == "none" or 
        "empty response" in final_answer.lower() or
        "i am sorry" in final_answer.lower() # Opzionale, dipende dal modello
    )

    if is_empty:
        final_answer = "Non ho informazioni sufficienti nei documenti per rispondere a questa domanda."

    used_contexts = [node.get_content() for node in response.source_nodes]

    chunks_debug = []
    for rank, node_with_score in enumerate(response.source_nodes, start=1):
        score = getattr(node_with_score, 'score', 0.0)
        text = node_with_score.get_content()
        
        chunks_debug.append({
            "rank":      rank,
            "score":     round(score, 4) if score else "N/A",
            "relevance": "FILTERED_PASS",
            "doc_type":  node_with_score.metadata.get("type", "unknown"),
            "preview":   text[:200].replace("\n", " "),
            "source":    node_with_score.metadata.get("url", "N/A"),
        })

    # Log di debug in console
    global _query_counter
    _query_counter += 1
    print(
        f"{_query_counter}/{_total_questions} [RETRIEVAL] '{question[:50]}...' → {len(used_contexts)} nodes passed filter "
        # f"(Cutoff: {SIMILARITY_CUTOFF})"
    )

    return {
        "answer":   final_answer,
        "contexts": used_contexts, # Passati a Ragas per Faithfulness/Recall
        "chunks":   chunks_debug,   # Usati per il salvataggio CSV/Debug
    }


# ==============================================================================
# JUDGE LLM (custom pass/fail grading)
# ==============================================================================

judge_client = OpenAI(
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("LLM_API_BASE"),
)

JUDGE_SYSTEM_PROMPT = (
    "You are a strict evaluator. Your ONLY task is to output a JSON object. "
    "1. Analyze the Response against the Grading Notes. "
    "2. If the notes are satisfied, result is 'pass', otherwise 'fail'. "
    "3. NEVER write introductory text or reasoning. "
    "4. Output ONLY the JSON object. "
    "Example: {\"result\": \"pass\"}"
)

JUDGE_USER_TEMPLATE = (
    "Response: {response}\n"
    "Grading Notes: {grading_notes}\n"
    "Expected Answer: {ground_truth}\n\n"
    "Pass if the response is semantically equivalent to the Expected Answer, "
    "even if phrased differently. Fail only if key facts are wrong\n"
    'Return JSON: {{"result": "pass"}} or {{"result": "fail"}}'
)


def judge_score(response: str, grading_notes: str, ground_truth: str) -> str:
    """
    Call the judge LLM and return 'pass', 'fail', or 'error'.
    Searches for a JSON verdict anywhere in the response.
    """
    prompt = JUDGE_USER_TEMPLATE.format(
        response=response,
        ground_truth=ground_truth,
    )
    try:
        completion = judge_client.chat.completions.create(
            model=os.getenv("MODEL"),
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            **({"response_format": {"type": "json_object"}} if os.getenv("USE_JSON_FORMAT", "false").lower() == "true" else {}),
            max_tokens=2048,
            temperature=0.2,
        )

        msg = completion.choices[0].message
        raw = msg.content or ""

        if not raw.strip():
            raw = getattr(msg, "reasoning_content", "") or ""

        print(f"Judge raw response: repr={repr(raw[:200])}...")

        match = re.search(r'\{\s*"result"\s*:\s*"(pass|fail)"\s*\}', raw, re.IGNORECASE)
        if match:
            return match.group(1).lower()

        print("Judge: no valid verdict found in response")
        return "error"

    except Exception as e:
        print(f"Judge error: {type(e).__name__}: {e}")
        return "error"

# ==============================================================================
# RAGAS LLM + EMBEDDINGS (shared across all metrics)
# ==============================================================================

_ragas_async_client = AsyncOpenAI(
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("LLM_API_BASE"),
    timeout=600,
)

_ragas_llm = llm_factory(
    model=os.getenv("MODEL"),
    client=_ragas_async_client,
    max_tokens=int(os.getenv("MAX_TOKENS")),
)

_ragas_embeddings = RagasHFEmbeddings(model=os.getenv("EMBEDDING_MODEL"))

# ==============================================================================
# RAGAS METRIC SCORERS
# ==============================================================================

faithfulness_scorer = Faithfulness(llm=_ragas_llm, run_config=_run_config)

answer_correctness_scorer = AnswerCorrectness(
    llm=_ragas_llm,
    embeddings=_ragas_embeddings,
)

response_relevancy_scorer = AnswerRelevancy(
    llm=_ragas_llm,
    embeddings=_ragas_embeddings,
    run_config=_run_config
)
context_precision_scorer = ContextPrecisionWithReference(llm=_ragas_llm, run_config=_run_config)
context_recall_scorer = ContextRecall(llm=_ragas_llm, run_config=_run_config)

# ==============================================================================
# ASYNC SCORING HELPERS
# ==============================================================================

async def compute_faithfulness(question: str, answer: str, contexts: list[str], q: int = 0) -> float | None:
    """Grounding of the answer in retrieved context. No ground truth needed."""
    if not ENABLE_FAITHFULNESS:
        return None
    try:
        print(f"[{q}/{_total_questions}] faithfulness: '{question[:50]}'")
        result = await faithfulness_scorer.ascore(
            user_input=question,
            response=answer,
            retrieved_contexts=contexts,
        )
        return round(result.value, 4)
    except Exception as e:
        print(f"Faithfulness error: {type(e).__name__}: {e}")
        return None


async def compute_answer_correctness(question: str, answer: str, reference: str, q: int = 0) -> float | None:
    """
    Factual + semantic similarity vs ground truth.
    Combines statement-level F1 (TP/FP/FN) with embedding cosine similarity.
    """
    if not ENABLE_ANSWER_CORRECTNESS or not reference:
        return None
    try:
        print(f"[{q}/{_total_questions}] answer_correctness: '{question[:50]}'")
        result = await answer_correctness_scorer.ascore(
            user_input=question,
            response=answer,
            reference=reference,
        )
        return round(result.value, 4)
    except Exception as e:
        print(f"AnswerCorrectness error: {type(e).__name__}: {e}")
        return None


async def compute_response_relevancy(question: str, answer: str, contexts: list[str], q: int = 0) -> float | None:
    if not ENABLE_RESPONSE_RELEVANCY:
        return None
    try:
        print(f"[{q}/{_total_questions}] response_relevancy: '{question[:50]}'")
        result = await response_relevancy_scorer.ascore(
            user_input=question,
            response=answer,
            # AnswerRelevancy does not take retrieved_contexts
        )
        return round(result.value, 4)
    except Exception as e:
        print(f"ResponseRelevancy error: {type(e).__name__}: {e}")
        return None


async def compute_context_precision(
    question: str, answer: str, contexts: list[str], reference: str, q: int = 0
) -> float | None:
    if not ENABLE_CONTEXT_PRECISION or not reference:
        return None
    try:
        print(f"[{q}/{_total_questions}] context_precision: '{question[:50]}'")
        result = await context_precision_scorer.ascore(
            user_input=question,
            # ContextPrecisionWithReference does not take response
            retrieved_contexts=contexts,
            reference=reference,
        )
        return round(result.value, 4)
    except Exception as e:
        print(f"ContextPrecision error: {type(e).__name__}: {e}")
        return None

async def compute_context_recall(
    question: str, contexts: list[str], reference: str, q: int = 0
) -> float | None:
    """
    Does the retrieved context cover all key facts in the ground truth?
    Low recall = the retriever missed important information.
    """
    if not ENABLE_CONTEXT_RECALL or not reference:
        return None
    try:
        print(f"[{q}/{_total_questions}] context_recall: '{question[:50]}'")
        result = await context_recall_scorer.ascore(
            user_input=question,
            retrieved_contexts=contexts,
            reference=reference,
        )
        return round(result.value, 4)
    except Exception as e:
        print(f"ContextRecall error: {type(e).__name__}: {e}")
        return None


# ==============================================================================
# DATASET
# ==============================================================================

def load_dataset() -> Dataset:
    """
    Define the evaluation dataset.
    Fields:
        question       — query sent to the RAG
        grading_notes  — key points the answer must cover (used by judge)
        ground_truth   — reference answer (used by RAGAS metrics)
    """
    dataset = Dataset(
        name="test_dataset",
        backend="local/csv",
        root_dir="evals",
    )


    for sample in samples:
        dataset.append(sample)

    dataset.save()
    return dataset


# ==============================================================================
# EXPERIMENT
# ==============================================================================

_index = load_index(INDEX_DIR)  # loaded once at module level, reused for every row
_query_counter = 0
_total_questions = 0

# limit_concurrency = asyncio.Semaphore(1)
@experiment()
async def run_experiment(row: dict) -> dict:
    # async with limit_concurrency:
        try:
            rag_result = query_rag(_index, row["question"])
            q = _query_counter  # snapshot before parallel scoring shifts the counter
            answer     = rag_result["answer"]
            contexts   = rag_result["contexts"]
            reference  = row.get("ground_truth", "")

            print(f" -> Judge's Rating for: {row['question'][:30]}...")
            score = await asyncio.to_thread(
                judge_score, answer, row["grading_notes"], reference
            )
            faithfulness = await compute_faithfulness(row["question"], answer, contexts, q)
            answer_correctness = await compute_answer_correctness(row["question"], answer, reference, q)
            response_relevancy = await compute_response_relevancy(row["question"], answer, contexts, q)
            context_precision = await compute_context_precision(row["question"], answer, contexts, reference, q)
            context_recall = await compute_context_recall(row["question"], contexts, reference, q)

            result = {
                "question":        row["question"],
                # "grading_notes":   row["grading_notes"],
                "ground_truth":    reference,
                "answer":          answer,
                "contexts":        "\n".join(f"{i+1}): (len: {len(ctx)}) (score: {rag_result['chunks'][i]['score']:.4f}) {ctx[:30]}..." for i, ctx in enumerate(contexts)),
                "judge_result":    score,
                "top_chunk_score": rag_result["chunks"][0]["score"] if rag_result["chunks"] else None,
                "top_chunk_src":   rag_result["chunks"][0]["source"] if rag_result["chunks"] else None,
            }
            if ENABLE_ANSWER_CORRECTNESS:
                result["answer_correctness"] = answer_correctness
            if ENABLE_FAITHFULNESS:
                result["faithfulness"] = faithfulness
            if ENABLE_RESPONSE_RELEVANCY:
                result["response_relevancy"] = response_relevancy
            if ENABLE_CONTEXT_PRECISION:
                result["context_precision"] = context_precision
            if ENABLE_CONTEXT_RECALL:
                result["context_recall"] = context_recall
            return result

        except Exception as e:
            print(f"Experiment error: {type(e).__name__}: {e}")
            return {"question": row["question"], "judge_result": "error"}


# ==============================================================================
# ENTRY POINT
# ==============================================================================
import time

async def main():

    global _total_questions, _query_counter
    dataset = load_dataset()
    _total_questions = len(dataset)
    _query_counter = 0
    print(f"Dataset loaded: {_total_questions} samples")
    start_time = time.time()


    experiment_results = await run_experiment.arun(dataset, name=OUTPUT_FILENAME)
    print("Experiment completed.")

    # Sort results to match original dataset order
    questions_order = [s["question"] for s in dataset]
    experiment_results._data = sorted(
        experiment_results._data,
        key=lambda r: questions_order.index(r["question"]),
    )

    experiment_results.save()
    print(f"Results saved to: evals/experiments/{experiment_results.name}.csv\n")
    print(f"Time needed: {format_time(time.time() - start_time)}")


if __name__ == "__main__":
    asyncio.run(main())