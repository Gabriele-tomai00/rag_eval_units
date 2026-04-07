import os
import json
import asyncio
from dotenv import load_dotenv
import re

import chromadb
from openai import OpenAI

from llama_index.core import VectorStoreIndex, Settings, StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai_like import OpenAILike
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.postprocessor import SimilarityPostprocessor

from ragas import Dataset, experiment

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
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HUGGINGFACE_HUB_VERBOSITY"] = "error"

load_dotenv()

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# INDEX_DIR         = "../rag/rag_index_sentence_splitting"
# OUTPUT_FILENAME   = "from_sentence_splitting_index_results"

# INDEX_DIR         = "../rag/rag_index_markdown_chunking"
# OUTPUT_FILENAME   = "from_rag_index_markdown_chunking_results"

INDEX_DIR         = "../rag/rag_index_markdown_and_sentence_chunking"
OUTPUT_FILENAME   = "from_rag_index_markdown_and_sentence_chunking_results"

SIMILARITY_TOP_K  = 7
SIMILARITY_CUTOFF = 0.35
SCORE_THRESHOLDS  = {"high": 0.7, "medium": 0.6}

# Feature flags — disable expensive metrics during quick debug runs
ENABLE_JUDGE                    = True
ENABLE_FAITHFULNESS             = True
ENABLE_ANSWER_CORRECTNESS       = True
ENABLE_RESPONSE_RELEVANCY       = True
ENABLE_CONTEXT_PRECISION        = True
ENABLE_CONTEXT_RECALL           = True

from ragas.run_config import RunConfig

# Conservative config for a local/unstable vLLM service
_run_config = RunConfig(
    max_workers=4,
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
            "Rispondi sempre in italiano. "
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
    Run a full RAG query: retrieve chunks + generate answer.

    Returns
    -------
    dict:
        answer   : str        — LLM-generated answer
        contexts : list[str]  — raw chunk texts
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

    query_engine = index.as_query_engine(
        similarity_top_k=SIMILARITY_TOP_K,
        node_postprocessors=[
            SimilarityPostprocessor(similarity_cutoff=SIMILARITY_CUTOFF)
        ]
    )
    response = query_engine.query(question)

    filtered_chunks = [c for c in chunks if c["score"] < SIMILARITY_CUTOFF]
    print(
        f"[RETRIEVAL] '{question[:50]}...' → {len(nodes)} retrieved, "
        f"{len(filtered_chunks)} under threshold ({SIMILARITY_CUTOFF})"
    )

    return {
        "answer":   str(response.response),
        "contexts": contexts,
        "chunks":   chunks,
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
    'Return JSON: {{"result": "pass"}} or {{"result": "fail"}}'
)


def judge_score(response: str, grading_notes: str, ground_truth: str) -> str:
    """
    Call the judge LLM and return 'pass', 'fail', or 'error'.
    Searches for a JSON verdict anywhere in the response.
    """
    prompt = JUDGE_USER_TEMPLATE.format(
        response=response,
        grading_notes=grading_notes,
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
            temperature=0.0,
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

async def compute_faithfulness(question: str, answer: str, contexts: list[str]) -> float | None:
    """Grounding of the answer in retrieved context. No ground truth needed."""
    if not ENABLE_FAITHFULNESS:
        return None
    try:
        result = await faithfulness_scorer.ascore(
            user_input=question,
            response=answer,
            retrieved_contexts=contexts,
        )
        return round(result.value, 4)
    except Exception as e:
        print(f"Faithfulness error: {type(e).__name__}: {e}")
        return None


async def compute_answer_correctness(question: str, answer: str, reference: str) -> float | None:
    """
    Factual + semantic similarity vs ground truth.
    Combines statement-level F1 (TP/FP/FN) with embedding cosine similarity.
    """
    if not ENABLE_ANSWER_CORRECTNESS or not reference:
        return None
    try:
        result = await answer_correctness_scorer.ascore(
            user_input=question,
            response=answer,
            reference=reference,
        )
        return round(result.value, 4)
    except Exception as e:
        print(f"AnswerCorrectness error: {type(e).__name__}: {e}")
        return None


async def compute_response_relevancy(question: str, answer: str, contexts: list[str]) -> float | None:
    if not ENABLE_RESPONSE_RELEVANCY:
        return None
    try:
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
    question: str, answer: str, contexts: list[str], reference: str
) -> float | None:
    if not ENABLE_CONTEXT_PRECISION or not reference:
        return None
    try:
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
    question: str, contexts: list[str], reference: str
) -> float | None:
    """
    Does the retrieved context cover all key facts in the ground truth?
    Low recall = the retriever missed important information.
    """
    if not ENABLE_CONTEXT_RECALL or not reference:
        return None
    try:
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

    samples = [
            {
                "question": "sede dell'università di Trieste",
                "grading_notes": "deve menzionare Piazzale Europa e Trieste",
                "ground_truth": (
                    "La sede principale dell'Università degli Studi di Trieste si trova a Trieste, "
                    "in Piazzale Europa 1, in un'area sopraelevata rispetto al centro della città."
                ),
            },
            {
                "question": "in quale edificio, piano e aula stampare all università",
                "grading_notes": "edificio H3, 5 piano, aule informatiche",
                "ground_truth": (
                    "È possibile stampare presso l'edificio H3, situato nel polo di Piazzale Europa, "
                    "al quinto piano all'interno delle aule informatiche."
                ),
            },
            {
                "question": "obiettivi formativi ingegneria elettronica e informatica: Capacità di applicare conoscenza e comprensione per curriculum Ingegneria biomedica",
                "grading_notes": "esercitazioni, laboratori e strumenti didattici",
                "ground_truth": (
                    "L'obiettivo è formare laureati capaci di affrontare problemi dell'ingegneria dell'informazione e biomedica. "
                    "Lo studio è affiancato da esercitazioni scritte e in laboratorio. Gli strumenti includono lezioni ordinarie, "
                    "integrative, seminari ed esercitazioni, con valutazioni tramite verifiche scritte, orali e prova finale."
                ),
            },
            {
                "question": "titolo di studio richiesto per immatricolazione",
                "grading_notes": "diploma superiore e nota sui titoli esteri",
                "ground_truth": (
                    "Il titolo richiesto è il diploma di scuola media superiore o titolo estero equipollente. "
                    "Per i titoli esteri è necessario verificare la validità presso la sezione Studenti Internazionali."
                ),
            },
            {
                "question": "quali sono i vari curriculum del corso Scienze e Tecnologie per l'ambiente e la natura",
                "grading_notes": "Ambientale, Biologico e Didattico",
                "ground_truth": "I curriculum sono tre: Ambientale, Biologico e Didattico.",
            },
            {
                "question": "contatti e ufficio tasse",
                "grading_notes": "indirizzo, telefono, mail e orari sportello",
                "ground_truth": (
                    "Ufficio Applicativi per la carriera dello studente e i contributi universitari: Piazzale Europa 1, Edificio A. "
                    "Tel: +39 040 558 3731 (mar, mer, ven 12-13). Email: tasse.studenti@amm.units.it. "
                    "Sportello su prenotazione (EasyPlanning): Lunedì 15:00-16:40 e Giovedì 09:00-11:10."
                ),
            },
            {
                "question": "parlami dell iniziativa Climbing for Climate (CFC)",
                "grading_notes": "RUS, CAI e sensibilizzazione riscaldamento globale",
                "ground_truth": (
                    "Iniziativa promossa da RUS e CAI per sensibilizzare sul riscaldamento globale. "
                    "Il nome richiama i clorofluorocarburi (CFC), gas responsabili del buco nell'ozono banditi dal Protocollo di Montreal. "
                    "L'ateneo partecipa organizzando eventi sul territorio."
                ),
            },
            {
                "question": "inizio e fine lezioni primo semestre SCIENZE INTERNAZIONALI E DIPLOMATICHE",
                "grading_notes": "22 settembre - 19 dicembre 2025 (1 ottobre per I anno)",
                "ground_truth": (
                    "Le lezioni iniziano il 22 settembre 2025 (il 1 ottobre per gli studenti del primo anno) "
                    "e terminano il 19 dicembre 2025."
                ),
            },
            {
                "question": "inizio e fine lezioni primo semestre SCIENZE E TECNICHE PSICOLOGICHE",
                "grading_notes": "22/29 settembre - 19 dicembre 2025",
                "ground_truth": (
                    "Il primo semestre inizia il 29 settembre 2025 per il I anno e il 22 settembre per gli anni successivi, "
                    "con termine il 19 dicembre 2025 per tutti."
                ),
            },
            {
                "question": "dove trovare il materiale didattico del corso di DIGITAL ELECTRONICS AND DEVICES",
                "grading_notes": "Moodle, MS Teams e link docente",
                "ground_truth": (
                    "Il materiale (slide ed esercizi) è disponibile su Moodle e MS Teams o sul sito del docente: "
                    "http://www2.units.it/carrato/didatt/DSE_web/index.html"
                ),
            },
            {
                "question": "dove trovare il materiale didattico del corso di Cybersecurity",
                "grading_notes": "link bartolialberto.github.io",
                "ground_truth": (
                    "Il materiale del corso è disponibile sul sito: https://bartolialberto.github.io/CybersecurityCourse/"
                ),
            },
            {
                "question": "l aula T dell'edificio A è libera il giorno 20 marzo 2026?",
                "grading_notes": "ammettere mancanza di info",
                "ground_truth": "Non ho informazioni sulla disponibilità dell'aula T per quella data specifica.",
            },
            {
                "question": "dimmi i corsi disponibili del dipartimento di musicologia",
                "grading_notes": "ammettere mancanza di info",
                "ground_truth": "Non dispongo di informazioni sui corsi del dipartimento di Musicologia.",
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

limit_concurrency = asyncio.Semaphore(1)
@experiment()
async def run_experiment(row: dict) -> dict:
    async with limit_concurrency:
        try:
            rag_result = query_rag(_index, row["question"])
            answer     = rag_result["answer"]
            contexts   = rag_result["contexts"]
            reference  = row.get("ground_truth", "")
            
            print(f" -> Valutazione Judge per: {row['question'][:30]}...")
            score = await asyncio.to_thread(
                judge_score, answer, row["grading_notes"], reference
            )

            faithfulness = await compute_faithfulness(row["question"], answer, contexts)
            answer_correctness = await compute_answer_correctness(row["question"], answer, reference)
            response_relevancy = await compute_response_relevancy(row["question"], answer, contexts)
            context_precision = await compute_context_precision(row["question"], answer, contexts, reference)
            context_recall = await compute_context_recall(row["question"], contexts, reference)

            return {
                "question":            row["question"],
                "grading_notes":       row["grading_notes"],
                "ground_truth":        reference,
                "answer":              answer,
                "contexts":            "\n".join(f"{i+1}): (len: {len(ctx)}) {ctx[:30]}..." for i, ctx in enumerate(contexts)),
                "judge_result":        score,
                "answer_correctness":  answer_correctness,
                "faithfulness":        faithfulness,
                "response_relevancy":  response_relevancy,
                "context_precision":   context_precision,
                "context_recall":      context_recall,
                "top_chunk_score":     rag_result["chunks"][0]["score"] if rag_result["chunks"] else None,
                "top_chunk_src":       rag_result["chunks"][0]["source"] if rag_result["chunks"] else None,
            }

        except Exception as e:
            print(f"Experiment error: {type(e).__name__}: {e}")
            return {
                "question": row["question"],
                "judge_result": "error",
                "faithfulness":       None,
                "answer_correctness": None,
                "response_relevancy": None,
                "context_precision":  None,
                "context_recall":     None,
            }


# ==============================================================================
# ENTRY POINT
# ==============================================================================
import time

async def main():

    dataset = load_dataset()
    print(f"Dataset loaded: {len(dataset)} samples")
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
    print(f"Results saved to: evals/experiments/{experiment_results.name}.csv")
    end_time = time.time()
    print(f"Total execution time: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())