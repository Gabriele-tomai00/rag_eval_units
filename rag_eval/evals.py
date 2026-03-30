import os
import json
import asyncio

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

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ==============================================================================
# CONFIGURATION
# ==============================================================================

INDEX_DIR         = "rag_index"
SIMILARITY_TOP_K  = 5
SIMILARITY_CUTOFF = 0.35
SCORE_THRESHOLDS  = {"high": 0.7, "medium": 0.6}
CONTEXT_WINDOW    = 8192
MAX_TOKENS        = 1024

# Feature flags — disable expensive metrics during quick debug runs
ENABLE_JUDGE                    = True
ENABLE_FAITHFULNESS             = True
ENABLE_ANSWER_CORRECTNESS       = True
ENABLE_RESPONSE_RELEVANCY       = True
ENABLE_CONTEXT_PRECISION        = True
ENABLE_CONTEXT_RECALL           = True

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
    temperature=0,
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
        f"[RETRIEVAL] '{question[:50]}' → {len(nodes)} retrieved, "
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
    api_key="anything",
    base_url="http://localhost:4000/v1",
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
    Extracts the verdict from the last line, allowing the model to reason freely.
    """
    prompt = JUDGE_USER_TEMPLATE.format(
        response=response,
        grading_notes=grading_notes,
        ground_truth=ground_truth,
    )
    try:
        completion = judge_client.chat.completions.create(
            model="ggml-org/gpt-oss-120b-GGUF",
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=512,
            temperature=0.0,
        )

        msg = completion.choices[0].message
        raw = msg.content or ""

        # Some models return the answer in reasoning_content when content is empty
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
# RAGAS LLM + EMBEDDINGS (shared across all metrics)
# ==============================================================================

_ragas_async_client = AsyncOpenAI(
    api_key="anything",
    base_url="http://172.30.42.129:8080/v1",
    timeout=300,
)

_ragas_llm = llm_factory(
    model="openai/ggml-org/gpt-oss-120b-GGUF",
    client=_ragas_async_client,
    max_tokens=4096,
    timeout=300,
    max_retries=2,
)

_ragas_embeddings = RagasHFEmbeddings(model="BAAI/bge-m3")

# ==============================================================================
# RAGAS METRIC SCORERS
# ==============================================================================

faithfulness_scorer = Faithfulness(llm=_ragas_llm)

answer_correctness_scorer = AnswerCorrectness(
    llm=_ragas_llm,
    embeddings=_ragas_embeddings,
)

response_relevancy_scorer = AnswerRelevancy(
    llm=_ragas_llm,
    embeddings=_ragas_embeddings,
)
context_precision_scorer = ContextPrecisionWithReference(llm=_ragas_llm)
context_recall_scorer = ContextRecall(llm=_ragas_llm)

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
        # {
        #     "question":      "sede dell'università di Trieste",
        #     "grading_notes": "deve menzionare Piazzale Europa e Trieste",
        #     "ground_truth":  "La sede principale dell Università degli Studi di Trieste è a Trieste, in Piazzale Europa 1, su un area sopraelevata rispetto al centro della città.",
        # },
        # {
        #     "question":      "in quale edificio, piano e aula stampare all università",
        #     "grading_notes": "deve menzionare dove è possibile stampare (edificio, piano, aula) o chi contattare",
        #     "ground_truth":  "È possibile stampare presso l'edificio H3, quinto piano, aula informatica.",
        # },
        # {
        #     "question":      "obiettivi formativi ingegneria elettronica e informatica: Capacità di applicare conoscenza e comprensione per curriculum Ingegneria biomedica",
        #     "grading_notes": "deve includere il fatto che si fanno esercitazioni e laboratorio, gli strumenti didattici utilizzati",
        #     "ground_truth":  (
        #         "I laureati in Ingegneria Elettronica e Informatica, curriculum ingegneria biomedica, devono avere una conoscenza "
        #         "sufficientemente ampia da essere in grado di affrontare problemi che coinvolgono ambiti diversi dell'Ingegneria "
        #         "dell'Informazione, e in particolare l'ambito biomedica. "
        #         "Lo studio delle conoscenze di base e' quindi affiancato da esercitazioni scritte ed in laboratorio: per prendere "
        #         "confidenza con le nozioni trattate durante i corsi, infatti, gli esercizi scritti e le prove di laboratorio previste "
        #         "forzano l'allievo ad applicare le conoscenze ed i concetti acquisiti. "
        #         "Gli strumenti didattici utilizzati per conseguire i suddetti obiettivi sono lezioni ordinarie, lezioni integrative, "
        #         "seminari, esercitazioni. L'acquisizione delle conoscenze e' valutata mediante verifiche orali e/o scritte, nonche' "
        #         "tramite la prova finale."
        #     ),
        # },
        # {
        #     "question":      "scadenza per immatricolazione",
        #     "grading_notes": "deve includere la data di scadenza per immatricolarsi per l'a.a. 2025/26",
        #     "ground_truth":  "Immatricolazioni dal 9 giugno al 6 ottobre 2025. Riapertura dal 14 gennaio 2026 al 6 marzo 2026.",
        # },
        # {
        #     "question":      "quali sono i vari curriculum del corso Scienze e Tecnologie per l'ambiente e la natura",
        #     "grading_notes": "deve indicare 3 diversi percorsi di studio/curriculum",
        #     "ground_truth":  "Curriculum Ambientale, Biologico e Didattico",
        # },
        {
            "question":      "contatti e ufficio tasse",
            "grading_notes": "deve includere almeno un numero di telefono e una mail e il nome dell ufficio",
            "ground_truth":  ("Telefono: +39 040 558 3731 (martedì, mercoledì, venerdì 12:00 13:00). Email: tasse.studenti@amm.units.it. "
                              "Ufficio Applicativi per la carriera dello studente e i contributi universitari"),
        },
        # {
        #     "question":      "parlami dell iniziativa Climbing for Climate (CFC)",
        #     "grading_notes": "deve indicare un iniziativa organizzata dalla RUS",
        #     "ground_truth":  (
        #         "Climbing for Climate (CFC) è un iniziativa promossa dalla Rete delle Università per lo Sviluppo Sostenibile (RUS) "
        #         "in collaborazione con il Club Alpino Italiano (CAI). "
        #         "L obiettivo principale è coinvolgere le istituzioni accademiche nella lotta contro il riscaldamento globale, attraverso "
        #         "la formazione di studenti, la promozione di ricerche orientate allo sviluppo sostenibile e la sensibilizzazione della "
        #         "cittadinanza. "
        #         "Il progetto prende il nome anche dall acronimo CFC, che indica i clorofluorocarburi, composti chimici contenenti cloro, "
        #         "fluoro e carbonio. Queste sostanze, responsabili della riduzione dello strato di ozono e dotate di un forte effetto serra, "
        #         "sono state bandite dalla produzione con il Protocollo di Montreal del 1987."
        #     ),
        # },
        # {
        #     "question":      "inizio e fine lezioni primo semestre SCIENZE INTERNAZIONALI E DIPLOMATICHE",
        #     "grading_notes": "deve indicare giorno di inizio e giorno di fine per l'anno scolastico 2025",
        #     "ground_truth":  "dal 22 settembre 2025 al 19 dicembre 2025",
        # },
        # {
        #     "question":      "inizio e fine lezioni primo semestre SCIENZE E TECNICHE PSICOLOGICHE",
        #     "grading_notes": "deve indicare giorno di inizio e giorno di fine per l'anno scolastico 2025",
        #     "ground_truth":  "I anno: dal 29 settembre 2025 al 19 dicembre 2025. II e III anno: dal 22 settembre 2025 al 19 dicembre 2025",
        # },
        # # Expected failures — RAG should admit it doesn't know
        # {
        #     "question":      "l aula T dell'edificio A è libera il giorno 20 marzo 2026?",
        #     "grading_notes": "deve ammettere di non avere informazioni sufficienti, NON deve inventare un contenuto",
        #     "ground_truth":  "Non ho informazioni su questo argomento",
        # },
        # {
        #     "question":      "dimmi i corsi disponibili del dipartimento di musicologia",
        #     "grading_notes": "deve ammettere di non avere informazioni sufficienti, NON deve inventare un contenuto",
        #     "ground_truth":  "Non ho informazioni su questo argomento",
        # },
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
    try:
        rag_result = query_rag(_index, row["question"])
        answer     = rag_result["answer"]
        contexts   = rag_result["contexts"]
        reference  = row.get("ground_truth", "")

        # Run all scorers concurrently — they are fully independent
        (
            score,
            faithfulness,
            answer_correctness,
            response_relevancy,
            context_precision,
            context_recall,
        ) = await asyncio.gather(
            asyncio.to_thread(
                judge_score,
                answer,
                row["grading_notes"],
                reference,
            ),
            compute_faithfulness(row["question"], answer, contexts),
            compute_answer_correctness(row["question"], answer, reference),
            compute_response_relevancy(row["question"], answer, contexts),
            compute_context_precision(row["question"], answer, contexts, reference),
            compute_context_recall(row["question"], contexts, reference),
        )

        return {
            "question":            row["question"],
            "grading_notes":       row["grading_notes"],
            "ground_truth":        reference,
            "answer":              answer,
            "contexts":            " | ".join(ctx[:30] + "..." for ctx in contexts),
            # "contexts":            " | ".join(ctx + "\n ------------------------------------------------------ \n\n" for ctx in contexts),
            "judge_result":               score,
            "answer_correctness":  answer_correctness,
            # RAGAS — answer quality
            "faithfulness":        faithfulness,
            "response_relevancy":  response_relevancy,
            # RAGAS — retrieval quality
            "context_precision":   context_precision,
            "context_recall":      context_recall,
            # Debug
            "top_chunk_score":     rag_result["chunks"][0]["score"]  if rag_result["chunks"] else None,
            "top_chunk_src":       rag_result["chunks"][0]["source"] if rag_result["chunks"] else None,
        }

    except Exception as e:
        print(f"Experiment error: {type(e).__name__}: {e}")
        return {
            "question":           row["question"],
            "judge_result":       "error",
            "faithfulness":       None,
            "answer_correctness": None,
            "response_relevancy": None,
            "context_precision":  None,
            "context_recall":     None,
        }


# ==============================================================================
# ENTRY POINT
# ==============================================================================

async def main():
    dataset = load_dataset()
    print(f"Dataset loaded: {len(dataset)} samples")

    experiment_results = await run_experiment.arun(dataset)
    print("Experiment completed.")

    # Sort results to match original dataset order
    questions_order = [s["question"] for s in dataset]
    experiment_results._data = sorted(
        experiment_results._data,
        key=lambda r: questions_order.index(r["question"]),
    )

    experiment_results.save()
    print(f"Results saved to: evals/experiments/{experiment_results.name}.csv")


if __name__ == "__main__":
    asyncio.run(main())