"""
Simple debug helper to query the persisted Chroma vectorstores for a term.

Usage:
  # from project root
  python .\backend\troubleshooting\debug_search.py IN0042923 --k 3

This will print whether the query returns any documents and the first 400 characters
of each matched document to help you decide if the vectorstore needs rebuilding.
"""
import os
import sys
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv

load_dotenv()

HERE = os.path.dirname(__file__)
os.environ.setdefault("AZURE_OPENAI_API_KEY", os.getenv("AZURE_OPENAI_API_KEY", ""))

def load_embeddings():
    return AzureOpenAIEmbeddings(
        azure_deployment=os.getenv("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME"),
        model=os.getenv("AZURE_OPENAI_EMBEDDINGS_MODEL_NAME", "text-embedding-3-large"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("AZURE_OPENAI_API_BASE"),
        openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION") or os.getenv("OPENAI_API_VERSION"),
    )

def search_kb(query: str, k: int = 3):
    emb = load_embeddings()
    persist_dir = os.path.join(HERE, ".chroma_kb")
    if not os.path.exists(persist_dir):
        print("KB vectorstore not found at", persist_dir)
        return
    store = Chroma(embedding_function=emb, persist_directory=persist_dir)
    results = store.similarity_search(query, k=k)
    print(f"KB: found {len(results)} results for '{query}'")
    for i, doc in enumerate(results, 1):
        snippet = doc.page_content[:400].replace('\n', ' ')
        print(f"--- Result {i} ---\n{snippet}\n")

def search_sla(query: str, k: int = 3):
    emb = load_embeddings()
    persist_dir = os.path.join(HERE, ".chroma_sla")
    if not os.path.exists(persist_dir):
        print("SLA vectorstore not found at", persist_dir)
        return
    store = Chroma(embedding_function=emb, persist_directory=persist_dir)
    results = store.similarity_search(query, k=k)
    print(f"SLA: found {len(results)} results for '{query}'")
    for i, doc in enumerate(results, 1):
        snippet = doc.page_content[:400].replace('\n', ' ')
        print(f"--- Result {i} ---\n{snippet}\n")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python debug_search.py <query> [--k N]")
        sys.exit(1)
    query = sys.argv[1]
    k = 3
    if "--k" in sys.argv:
        try:
            k = int(sys.argv[sys.argv.index("--k") + 1])
        except Exception:
            pass
    print("Searching for:", query)
    search_kb(query, k=k)
    search_sla(query, k=k)
