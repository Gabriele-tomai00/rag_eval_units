from llama_index.core import Settings
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from utils_rag import *
import asyncio
from llama_index.llms.openai_like import OpenAILike

os.environ["TOKENIZERS_PARALLELISM"] = "false" # avoid warning messages

Settings.llm = OpenAILike(
    model="ggml-org/gpt-oss-120b-GGUF",
    api_base="http://172.30.42.129:8080/v1",
    api_key="not_necessary",
    context_window=65536,
    max_tokens=2048,
    temperature=0.2,
    is_chat_model=True, # for using the new /v1/chat/completions API: role: system (for pr)
    system_prompt=get_prompt_from_file("prompt_for_llm.txt"),
)
Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-m3"
)


# === TOOL: Search documents ===
async def search_documents(index, query: str) -> str:
    """Answer questions about the provided documents."""
    if index is None:
        return
    query_engine = index.as_query_engine(llm=Settings.llm)
    response = await query_engine.aquery(query)
    return str(response)

async def search_documents_with_debug(index, query: str) -> str:
    retriever = index.as_retriever(similarity_top_k=3)
    print("Searching in documents...")
    nodes = await retriever.aretrieve(query)
    high_relevance = [n for n in nodes if n.score >= 0.7]
    medium_relevance = [n for n in nodes if 0.5 <= n.score < 0.7]
    low_relevance = [n for n in nodes if n.score < 0.5]
    print(f"Found: {len(high_relevance)} high relevance, {len(medium_relevance)} medium relevance, {len(low_relevance)} low relevance nodes.")
    if high_relevance:
        best_score = max(n.score for n in high_relevance)
        print(f"Best match score: {best_score:.3f}")
    print("\nGenerating answer...")
    query_engine = index.as_query_engine(llm=Settings.llm)
    response = await query_engine.aquery(query)
    return str(response)




# === MAIN ===
async def main():


    index = load_or_create_index("rag_index_con_teams_e_book")
    if index is None:
        print("Failed to load or create the index.")
        exit(1)
    else:
        print(f"Index loaded successfully.\n Current size: {get_index_size(index)}")

# COMMENTO PER NON RICREARE IL RAG INDEX CON TEAMS E BOOK
    # add_to_index_book(index, "units_book.json")

    # print(f"Index size after addition: {get_index_size(index)}")

    # add_to_index_teams_code(index, "teams_codes.json")

    # print(f"Index size after second addition: {get_index_size(index)}")



    # print("\nQUESTION: Chi è Trevisan Martino?")
    # result = await search_documents(index, 
    #     "Chi è TREVISAN MARTINO?"
    # )
    # print("\nANSWER:")
    # print(result)
    # print("\n\n\n\n\n")
    # print("\nQUESTION: Chi è SALVATO ERICA?")
    # result = await search_documents(index, 
    #     "Chi è SALVATO ERICA?"
    # )
    # print("\nANSWER:")
    # print(result)
    # print("\n\n\n\n\n")


    # print("\nQUESTION: Chi è Trevisan Martino?")
    # result = await search_documents_with_debug(index, 
    #     "Chi è TREVISAN MARTINO?"
    # )
    # print("\nANSWER:")
    # print(result)
    # print("\n\n\n\n\n")



    # print("\nQUESTION: Chi è Martino Trevisan?")
    # result = await search_documents_with_debug(index, 
    #     "Chi è Martino Trevisan?"
    # )
    # print("\nANSWER:")
    # print(result)
    # print("\n\n\n\n\n")



    # print("QUESTION: Qual'è l'indirizzo email di Martino Trevisan?")
    # result = await search_documents(index, 
    #     "Qual'è l'indirizzo email di Martino Trevisan?"
    # )
    # print("\nANSWER:")
    # print(result)
    # print("\n\n\n\n\n")

    print("QUESTION: Guardando i codici teams, puoi dirmi quali materie insegna Martino Trevisan?")
    result = await search_documents(index, 
        "Qual'è l'indirizzo email di Martino Trevisan?"
    )
    print("\nANSWER:")
    print(result)
    print("\n\n\n\n\n")   


    print("QUESTION: Guardando i codici teams, puoi dirmi quali materie insegna il prof. Martino Trevisan?")
    result = await search_documents(index, 
        "Qual'è l'indirizzo email di Martino Trevisan?"
    )
    print("\nANSWER:")
    print(result)
    print("\n\n\n\n\n")

if __name__ == "__main__":
    asyncio.run(main())