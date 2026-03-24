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

from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.metrics.collections import Faithfulness

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ==============================================================================
# CONFIGURATION
# ==============================================================================

INDEX_DIR        = "rag_index"
SIMILARITY_TOP_K = 5
SIMILARITY_CUTOFF = 0.3
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

    query_engine = index.as_query_engine(
        similarity_top_k=SIMILARITY_TOP_K,
        node_postprocessors=[
            SimilarityPostprocessor(similarity_cutoff=SIMILARITY_CUTOFF)
        ]
    )
    response = query_engine.query(question)

    filtered_chunks = [c for c in chunks if c["score"] >= SIMILARITY_CUTOFF]
    print(f"[RETRIEVAL] '{question[:50]}' → {len(nodes)} retrieved, {len(filtered_chunks)} above threshold ({SIMILARITY_CUTOFF})")


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

# JUDGE_SYSTEM_PROMPT = (
#     "You are a strict evaluator. "
#     "You will receive a RAG response, grading notes (key points that MUST be covered), "
#     "and a ground truth answer (for reference only). "
#     "The grading notes are the PRIMARY evaluation criterion. "
#     "If the response satisfies the grading notes, output pass — "
#     "even if the wording differs from the ground truth. "
#     "Think step by step, then on the LAST LINE output ONLY a JSON object "
#     "with a single key 'result' whose value is 'pass' or 'fail'. "
#     "Example last line: {\"result\": \"pass\"}"
# )

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
# RAGAS METRICS SETUP
# Uses the same LiteLLM proxy as the judge, but via AsyncOpenAI client
# ==============================================================================

from ragas.llms import llm_factory
from ragas.run_config import RunConfig

_ragas_async_client = AsyncOpenAI(
    api_key="anything",
    base_url="http://172.30.42.129:8080/v1",
    timeout=300
)

_ragas_llm = llm_factory(
    model="openai/ggml-org/gpt-oss-120b-GGUF",
    client=_ragas_async_client,
    max_tokens=4096, 
    timeout=300,
    max_retries=2
)


faithfulness_scorer = Faithfulness(llm=_ragas_llm)

async def compute_faithfulness(
    question: str,
    answer: str,
    contexts: list[str],
) -> float | None:
    """
    Compute RAGAS Faithfulness score for a single RAG result.
    Returns a float in [0, 1] or None on error.
    """
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

# ==============================================================================
# DATASET
# ==============================================================================

def load_dataset() -> Dataset:
    """
    Define the evaluation dataset.
    Fields:
        question       — query sent to the RAG
        grading_notes  — key points the answer must cover
        ground_truth— ground truth (used by future Answer Correctness metric)
    """
    dataset = Dataset(
        name="test_dataset",
        backend="local/csv",
        root_dir="evals",
    )

    # samples = [
    #     {
    #         "question":        "obiettivi formativi ingegneria elettronica e informatica: Capacità di applicare conoscenza e comprensione per curriculum Ingegneria biomedica",
    #         "grading_notes":   "deve includere il fatto che si fanno esercitazioni e laboratorio, gli strumenti didattici utilizzati",
    #         "ground_truth":    "I laureati in Ingegneria Elettronica e Informatica, curriculum ingegneria biomedica, devono avere una conoscenza sufficientemente ampia da essere in grado di affrontare problemi che coinvolgono ambiti diversi dell'Ingegneria dell'Informazione, e in particolare l'ambito biomedica. "
    #                            " Lo studio delle conoscenze di base e' quindi affiancato da esercitazioni scritte ed in laboratorio: per prendere confidenza con le nozioni trattate durante i corsi, infatti, gli esercizi scritti e le prove di laboratorio previste forzano l'allievo ad applicare le conoscenze ed i concetti acquisiti. "
    #                            " Gli strumenti didattici utilizzati per conseguire i suddetti obiettivi sono lezioni ordinarie, lezioni integrative, seminari, esercitazioni. L'acquisizione delle conoscenze e' valutata mediante verifiche orali e/o scritte, nonche' tramite la prova finale.",
    #     }
    # ]



    samples = [
        {
            "question":        "sede dell'università di Trieste",
            "grading_notes":   "deve menzionare Piazzale Europa e Trieste",
            "ground_truth":    "Piazzale Europa 1, 34127 Trieste, Italia",
        },
        {
            "question":        "in quale edificio stampare all università",
            "grading_notes":   "deve menzionare dove è possibile stampare o chi contattare",
            "ground_truth":    "Sì, è possibile stampare presso l'edificio H3",
        },
        {
            "question":        "obiettivi formativi ingegneria elettronica e informatica: Capacità di applicare conoscenza e comprensione per curriculum Ingegneria biomedica",
            "grading_notes":   "deve includere il fatto che si fanno esercitazioni e laboratorio, gli strumenti didattici utilizzati",
            "ground_truth":    "I laureati in Ingegneria Elettronica e Informatica, curriculum ingegneria biomedica, devono avere una conoscenza sufficientemente ampia da essere in grado di affrontare problemi che coinvolgono ambiti diversi dell'Ingegneria dell'Informazione, e in particolare l'ambito biomedica. "
                               " Lo studio delle conoscenze di base e' quindi affiancato da esercitazioni scritte ed in laboratorio: per prendere confidenza con le nozioni trattate durante i corsi, infatti, gli esercizi scritti e le prove di laboratorio previste forzano l'allievo ad applicare le conoscenze ed i concetti acquisiti. "
                               " Gli strumenti didattici utilizzati per conseguire i suddetti obiettivi sono lezioni ordinarie, lezioni integrative, seminari, esercitazioni. L'acquisizione delle conoscenze e' valutata mediante verifiche orali e/o scritte, nonche' tramite la prova finale.",
        },
        {
            "question":        "scadenza per immatricolazione",
            "grading_notes":   "deve includere la data di scaenda per immatricolarsi per per l a.a. 2025/26",
            "ground_truth":    "Immatricolazioni dal 9 giugno al 6 ottobre 2025",
        },
        {
            "question":        "quali sono i vari curriculum del corso Scienze e Tecnologie per l'ambiente e la natura",
            "grading_notes":   "deve indicare 3 diversi percorsi di studio/curriculm",
            "ground_truth":    "Curriculum Ambientale, Biologico e Didattico",
        },
        {
            "question":        "contatti per info tasse",
            "grading_notes":   "deve indicare un ufficio o contatto specifico per le tasse universitarie",
            "ground_truth":    "Ufficio Applicativi per la carriera dello studente e i contributi universitari",
        },
        {
            "question":        "contatti dell ufficio tasse",
            "grading_notes":   "deve includere almeno un numero di telefono e una mail",
            "ground_truth":    "Servizio telefonico: Martedì, Mercoledì, Venerdì: 12.00 - 13.00 Telefono: +39 040 558 3731 E-mail: tasse.studenti@amm.units.it",
        },
        {
            "question":        "parlami dell iniziativa Climbing for Climate (CFC)",
            "grading_notes":   "deve indicare un iniziativa organizzata dalla RUS",
            "ground_truth":    "è organizzata dalla RUS- Rete delle Università per lo Sviluppo Sostenibile in collaborazione con il CAI-Club alpino italiano. CFC è anche l acronimo dei CloroFluoroCarburi, composti chimici contenenti cloro, fluoro e carbonio, che, essendo in parte responsabili della riduzione dello strato di ozono presente nella stratosfera, ed avendo un elevato effetto serra sono stati banditi dalla produzione a seguito del protocollo di Montreal del 1987. ",
        },
        {
            "question":        "inizio e fine lezioni primo semestre SCIENZE INTERNAZIONALI E DIPLOMATICHE",
            "grading_notes":   "deve indicare giorno di inizio e giorno di fine per l anno scolastico 2025",
            "ground_truth":    "dal 22 settembre 2025 al 19 dicembre 2025",
        },
        {
            "question":        "inizio e fine lezioni primo semestre SCIENZE E TECNICHE PSICOLOGICHE",
            "grading_notes":   "deve indicare giorno di inizio e giorno di fine per l anno scolastico 2025",
            "ground_truth":    "dal 29 settembre 2025 al 19 dicembre 2025",
        },
        # fail because document not present
        {
            "question":        "l aula T dell'edificio A è libera il giorno 20 marzo 2026?",
            "grading_notes":   "deve ammettere di non avere informazioni sufficienti, NON deve inventare un contenuto",
            "ground_truth":    "Non ho informazioni su questo argomento",
        },
        {
            "question":        "dimmi i corsi disponibili del dipartimento di musicologia",
            "grading_notes":   "deve ammettere di non avere informazioni sufficienti, NON deve inventare un contenuto",
            "ground_truth":    "Non ho informazioni su questo argomento",
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
    try:
        rag_result = query_rag(_index, row["question"])

        # Run judge + faithfulness concurrently — they're independent
        score, faithfulness = await asyncio.gather(
            asyncio.to_thread(          # judge_score is sync → run in thread
                judge_score,
                rag_result["answer"],
                row["grading_notes"],
                row.get("ground_truth", ""),
            ),
            compute_faithfulness(
                question=row["question"],
                answer=rag_result["answer"],
                contexts=rag_result["contexts"],
            ),
        )

        return {
            "question":          row["question"],
            "grading_notes":     row["grading_notes"],
            "ground_truth":      row.get("ground_truth", ""),
            "answer":            rag_result["answer"],
            "contexts":          " | ".join(ctx[:30] + "..." for ctx in rag_result["contexts"]),
            "score":             score,
            "faithfulness_score": faithfulness,
            "top_chunk_score":   rag_result["chunks"][0]["score"]  if rag_result["chunks"] else None,
            "top_chunk_src":     rag_result["chunks"][0]["source"] if rag_result["chunks"] else None,
        }
    except Exception as e:
        print(f"Experiment error: {type(e).__name__}: {e}")
        return {"question": row["question"], "score": "error", "faithfulness_score": None}


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
        key=lambda r: questions_order.index(r["question"])
    )

    experiment_results.save()
    print(f"Results saved to: evals/experiments/{experiment_results.name}.csv")


if __name__ == "__main__":
    asyncio.run(main())