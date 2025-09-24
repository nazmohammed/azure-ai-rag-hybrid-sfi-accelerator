from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.messages import HumanMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from llama_index.core import SimpleDirectoryReader  # keep only if you use it
import pandas as pd
import os
import glob
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# PII anonymization
from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_anonymizer import AnonymizerEngine
from typing import Tuple, Dict, Any
import re

_here_dir = os.path.dirname(__file__)
# Load the .env located in the backend directory explicitly so scripts launched from the repo root
# still pick up the Azure/OpenAI credentials stored in backend/.env
load_dotenv(os.path.join(_here_dir, ".env"))

# ===== Env =====
azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("AZURE_OPENAI_API_BASE")
azure_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
azure_embeddings_deployment_name = os.getenv("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME")
azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
PRESIDIO_LANGUAGE = os.getenv("PRESIDIO_LANGUAGE", "en")
# Whether to restore PII values into the final response (boolean env var: RESTORE_PII)
RESTORE_PII = os.getenv("RESTORE_PII", "true").lower() not in ("false", "0")

# Folders
HERE = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, ".."))

# Use absolute paths relative to project root so the code works regardless of CWD
EXCEL_FOLDER_PATH = os.path.join(PROJECT_ROOT, "data", "sla_tickets")
PDF_FOLDER_PATH = os.path.join(PROJECT_ROOT, "data", "kb_documents")

# ===== Presidio engines =====
# Create analyzer/anonymizer lazily to avoid importing spaCy/Presidio at module import time
_analyzer = None
_anonymizer = None

def get_analyzer():
    global _analyzer
    if _analyzer is None:
        from presidio_analyzer import AnalyzerEngine

        _analyzer = AnalyzerEngine()
    return _analyzer


def get_anonymizer():
    global _anonymizer
    if _anonymizer is None:
        from presidio_anonymizer import AnonymizerEngine

        _anonymizer = AnonymizerEngine()
    return _anonymizer

def anonymize_text(
    text: str,
    language: str = PRESIDIO_LANGUAGE,
    preserve_regex: str | None = None,
) -> str:
    """Anonymize text using Presidio, with optional preservation of patterns.

    Args:
        text: input text
        language: language for presidio
        preserve_regex: optional regex string; matches will be temporarily replaced with
            placeholders and restored after anonymization. Useful to keep ticket IDs like IN0042923.
    """
    if not text:
        return text

    # If we need to preserve some patterns (e.g. ticket IDs), replace them with placeholders
    preserved = []
    placeholder_prefix = "__PRESERVED__"
    working_text = text
    if preserve_regex:
        matches = re.findall(preserve_regex, text)
        for i, m in enumerate(matches):
            ph = f"{placeholder_prefix}{i}__"
            preserved.append((ph, m))
            working_text = working_text.replace(m, ph)

    results: list[RecognizerResult] = get_analyzer().analyze(text=working_text, language=language)
    if not results:
        # restore preserved tokens if any
        for ph, orig in preserved:
            working_text = working_text.replace(ph, orig)
        return working_text

    anonymized = get_anonymizer().anonymize(text=working_text, analyzer_results=results).text

    # restore preserved tokens
    for ph, orig in preserved:
        anonymized = anonymized.replace(ph, orig)

    # Friendly replacements: Presidio uses placeholders like <DATE_TIME>, <PERSON>, etc.
    # Convert them to more natural phrases for end-users while preserving anonymization.
    friendly = os.getenv("PRESIDIO_FRIENDLY_REPLACEMENTS", "true").lower() != "false"
    if friendly:
        replacements = {
            "<DATE_TIME>": "[REDACTED DATE/TIME]",
            "<PERSON>": "[REDACTED NAME]",
            "<PHONE_NUMBER>": "[REDACTED PHONE]",
            "<EMAIL_ADDRESS>": "[REDACTED EMAIL]",
            "<CREDIT_CARD>": "[REDACTED CARD]",
            "<SSN>": "[REDACTED SSN]",
        }
        for k, v in replacements.items():
            anonymized = anonymized.replace(k, v)

        # Replace any remaining placeholders like <IN_PAN> with a friendly token.
        # Special-case mappings for known tokens
        special_map = {
            "IN_PAN": "PAN",
        }

        def _friendly(match):
            token = match.group(1)
            if token in special_map:
                label = special_map[token]
            else:
                # remove common prefixes like IN_, ZZ_, etc.
                label = re.sub(r"^[A-Z]{1,3}_", "", token)
                label = label.replace("_", " ").title()
            return f"[REDACTED {label}]"

        anonymized = re.sub(r"<([A-Z0-9_]+)>", _friendly, anonymized)

    return anonymized


def anonymize_and_map(
    text: str,
    language: str = PRESIDIO_LANGUAGE,
    preserve_regex: str | None = None,
):
    """Anonymize text by replacing detected PII spans with unique placeholders.

    Returns a tuple (anonymized_text, mapping) where mapping is {placeholder: original_value}.
    This lets us safely send anonymized text to the LLM and then re-insert original values
    into the model's response.
    """
    if not text:
        return text, {}, {}

    # Protect preserved patterns (e.g., ticket IDs) by replacing them with temporary placeholders.
    preserved: list[tuple[str, str]] = []
    working_text = text
    placeholder_prefix = "__PRESERVED__"
    if preserve_regex:
        matches = re.findall(preserve_regex, text)
        for i, m in enumerate(matches):
            ph = f"{placeholder_prefix}{i}__"
            preserved.append((ph, m))
            working_text = working_text.replace(m, ph)

    # Analyze using Presidio to detect PII spans
    results: list[RecognizerResult] = get_analyzer().analyze(text=working_text, language=language)
    if not results:
        # nothing to anonymize; restore preserved tokens and return empty mapping
        for ph, orig in preserved:
            working_text = working_text.replace(ph, orig)
        preserved_map = {ph: orig for ph, orig in preserved}
        return working_text, {}, preserved_map

    # Build mapping and replace spans with placeholders. Sort by start to avoid offset shifts.
    spans = sorted(results, key=lambda r: r.start)
    mapping: Dict[str, str] = {}
    anonymized = []
    last_idx = 0
    pii_counter = 0
    for res in spans:
        # ensure indices are in range
        start = max(0, res.start)
        end = min(len(working_text), res.end)
        if start >= end:
            continue
        # append text before span
        anonymized.append(working_text[last_idx:start])
        ph = f"__PII_{pii_counter}__"
        original = working_text[start:end]
        mapping[ph] = original
        anonymized.append(ph)
        pii_counter += 1
        last_idx = end

    anonymized.append(working_text[last_idx:])
    anonymized_text = "".join(anonymized)

    # Build preserved_map for callers so they can re-insert preserved tokens if needed
    preserved_map = {ph: orig for ph, orig in preserved}

    # restore preserved tokens in the anonymized text that we return to the LLM
    for ph, orig in preserved:
        anonymized_text = anonymized_text.replace(ph, orig)

    return anonymized_text, mapping, preserved_map


def _inject_ticket_into_response(response_text: str, ticket_id: str) -> str:
    """If the model redacted the ticket identifier (for example: "ticket __[REDACTED NAME]__"),
    replace the redaction with the known ticket_id. Only replace redaction tokens that
    directly follow the word "ticket" to avoid replacing unrelated redactions.
    """
    if not response_text or not ticket_id:
        return response_text

    # Match patterns like: ticket __[REDACTED NAME]__, ticket [REDACTED NAME],
    # ticket number [REDACTED NAME], ticket # [REDACTED NAME]
    pattern = re.compile(r"(ticket(?:\s*(?:number|no\.?|#)?)\s*)(__?\[REDACTED[^\]]+\]__?)",
                         flags=re.IGNORECASE)

    def _repl(m):
        prefix = m.group(1)
        return f"{prefix}{ticket_id}"

    new_text = pattern.sub(_repl, response_text)

    # Also handle cases where the model used a redaction token without the word 'ticket'
    # but the response was otherwise empty of any identifier — as a fallback, if the
    # ticket id appears nowhere and there's exactly one redaction token, replace it.
    if ticket_id not in new_text:
        redaction_tokens = re.findall(r"__?\[REDACTED[^\]]+\]__?", new_text)
        if len(redaction_tokens) == 1:
            new_text = new_text.replace(redaction_tokens[0], ticket_id)

    return new_text

# ===== Embeddings =====
def initialize_embeddings():
    return AzureOpenAIEmbeddings(
        # IMPORTANT: use azure_deployment for langchain_openai 0.3.x
        azure_deployment=azure_embeddings_deployment_name,
        model=os.getenv("AZURE_OPENAI_EMBEDDINGS_MODEL_NAME", "text-embedding-3-large"),
        api_key=azure_api_key,
        azure_endpoint=azure_endpoint,
        openai_api_version=azure_openai_api_version,
        chunk_size=512,
    )

# ===== LLM =====
def initialize_llm():
    return AzureChatOpenAI(
        # IMPORTANT: use azure_deployment for langchain_openai 0.3.x
        azure_deployment=azure_deployment_name,
        api_key=azure_api_key,
        azure_endpoint=azure_endpoint,
        openai_api_version=azure_openai_api_version,
    )

# ===== Data loading helpers =====
def read_pdf(file_path: str):
    try:
        return SimpleDirectoryReader(input_files=[file_path]).load_data()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []

def load_kb_data():
    file_paths = glob.glob(f"{PDF_FOLDER_PATH}/*.pdf")
    all_documents = []
    if not file_paths:
        print(f"[warn] No PDFs found under {PDF_FOLDER_PATH}.")
    with ThreadPoolExecutor() as executor:
        results = executor.map(read_pdf, file_paths)
        for docs in results:
            all_documents.extend(docs)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = []
    for doc in all_documents:
        try:
            # SimpleDirectoryReader returns nodes with .text
            chunks.extend(text_splitter.split_text(doc.text or ""))
        except Exception as e:
            print(f"Split error on doc: {e}")
    return chunks

def _read_excel_rows(file_path: str):
    try:
        df = pd.read_excel(file_path, engine="openpyxl")
        return df.astype(str).apply(" ".join, axis=1).tolist()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []

def load_sla_data():
    file_paths = glob.glob(f"{EXCEL_FOLDER_PATH}/*.xlsx")
    if not file_paths:
        print(f"[warn] No Excel files found under {EXCEL_FOLDER_PATH}.")
    with ThreadPoolExecutor() as executor:
        all_rows_lists = list(executor.map(_read_excel_rows, file_paths))
    flat_rows = [row for rows in all_rows_lists for row in rows]
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=200)
    return text_splitter.split_text("\n".join(flat_rows))

def batch_documents(documents, batch_size, vectorstore):
    for i in range(0, len(documents), batch_size):
        batch = documents[i : i + batch_size]
        if batch:
            vectorstore.add_texts(batch)

# ===== Pipelines =====
def initialize_kb_rag_pipeline():
    embeddings = initialize_embeddings()
    llm = initialize_llm()
    persist_dir = os.path.join(HERE, ".chroma_kb")

    if os.path.exists(persist_dir):
        print("Loading persisted KB vectorstore...")
        vectorstore = Chroma(embedding_function=embeddings, persist_directory=persist_dir)
    else:
        print("Creating new KB vectorstore and persisting...")
        documents = load_kb_data()
        vectorstore = Chroma(embedding_function=embeddings, persist_directory=persist_dir)
        batch_documents(documents, batch_size=50, vectorstore=vectorstore)
        vectorstore.persist()
        print("KB vectorstore persisted.")

    class RAGPipeline:
        def run(self, user_message: str):
            # 1) Try to extract a ticket id from the user's question so we can use it for retrieval
            ticket_match = re.search(r"\b(IN\d{4,7})\b", user_message, re.IGNORECASE)
            ticket_id = ticket_match.group(1) if ticket_match else None

            # 2) For retrieval prefer the exact ticket id if present; fall back to the raw user message.
            # Do NOT anonymize before retrieval because that can remove matching tokens; instead
            # preserve ticket ids when needed and search using the ticket id (if present).
            retrieval_query = ticket_id if ticket_id else user_message
            results = vectorstore.similarity_search(retrieval_query, k=10)

            # 3) Build raw context from retrieved docs
            raw_context = " ".join([doc.page_content for doc in results])

            # 4) Anonymize context and question but keep a mapping of placeholders -> original PII
            anon_context, context_map, preserved_map = anonymize_and_map(raw_context, preserve_regex=r"\bIN\d{4,7}\b")
            anon_question, question_map, preserved_map_q = anonymize_and_map(user_message, preserve_regex=r"\bIN\d{4,7}\b")

            # Merge mappings so we can restore all originals later
            combined_map = {**context_map, **question_map}
            # Merge preserved maps (context vs question) too
            preserved_map = {**preserved_map, **preserved_map_q}

            # 5) LLM: send anonymized context and question. The model may reference placeholders like __PII_0__
            response = llm.invoke([
                HumanMessage(
                    content=f"""
You are a support assistant that answers questions based only on the retrieved data.

Important: The context and question have been anonymized; any PII values were replaced by placeholders
like __PII_0__, __PII_1__, etc. When you refer to ticket identifiers please use the exact ticket id provided
in the question (it will be visible as a preserved token). Do not invent new PII.

Context:
{anon_context}

Question: {anon_question}
Answer:"""
                )
            ])

            # 6) Restore original PII values into the model's response using the mapping.
            raw_response = response.content
            final_response = raw_response

            for ph, orig in combined_map.items():
                final_response = final_response.replace(ph, orig)
            # Replace preserved placeholders (like __PRESERVED__0__) with their original values (e.g., ticket id)
            for ph, orig in preserved_map.items():
                final_response = final_response.replace(ph, orig)

            # Ensure ticket id appears in the response header if missing
            if ticket_id and ticket_id not in final_response:
                final_response = f"Ticket: {ticket_id}\n\n" + final_response

            return final_response

    return RAGPipeline()

def initialize_sla_rag_pipeline():
    embeddings = initialize_embeddings()
    llm = initialize_llm()
    persist_dir = os.path.join(HERE, ".chroma_sla")

    if os.path.exists(persist_dir):
        print("Loading persisted SLA vectorstore...")
        vectorstore = Chroma(embedding_function=embeddings, persist_directory=persist_dir)
    else:
        print("Creating new SLA vectorstore and persisting...")
        documents = load_sla_data()
        vectorstore = Chroma(embedding_function=embeddings, persist_directory=persist_dir)
        batch_documents(documents, batch_size=50, vectorstore=vectorstore)
        vectorstore.persist()
        print("SLA vectorstore persisted.")

    class RAGPipeline:
        def run(self, user_message: str):
            # 1) Try to extract a ticket id from the user's question so we can use it for retrieval
            ticket_match = re.search(r"\b(IN\d{4,7})\b", user_message, re.IGNORECASE)
            ticket_id = ticket_match.group(1) if ticket_match else None

            # 2) For retrieval prefer the exact ticket id if present; fall back to the raw user message.
            # Do NOT anonymize before retrieval because that can remove matching tokens.
            retrieval_query = ticket_id if ticket_id else user_message
            retrieved_docs = vectorstore.similarity_search(retrieval_query, k=10)

            # 3) Build raw context from retrieved docs
            if not retrieved_docs:
                print(f"[info] No documents retrieved for query: {retrieval_query}")
                raw_context = ""
            else:
                print(f"[info] Retrieved {len(retrieved_docs)} documents for query: {retrieval_query}")
                raw_context = " ".join([doc.page_content for doc in retrieved_docs])

            # 4) Anonymize context and question but capture mapping to originals
            # Anonymize context and question (preserve ticket id tokens)
            anon_context, context_map, preserved_map = anonymize_and_map(
                raw_context, preserve_regex=r"\bIN\d{4,7}\b"
            )
            anon_question, question_map, preserved_map_q = anonymize_and_map(
                user_message, preserve_regex=r"\bIN\d{4,7}\b"
            )

            combined_map = {**context_map, **question_map}
            preserved_map = {**preserved_map, **preserved_map_q}

            # 5) LLM: send anonymized context/question to the model
            prompt = f"{anon_context}\n\nImportant: The context and question have been anonymized; any PII values were replaced by placeholders like __PII_0__. When returning the answer, do NOT invent new PII values. Use the preserved ticket id as provided.\n\nQuestion: {anon_question}\nAnswer:"
            response = llm.invoke([HumanMessage(content=prompt)])

            # 6) Restore original PII into the model's response using the mapping
            raw_response = response.content
            final_response = raw_response

            if RESTORE_PII:
                for ph, orig in combined_map.items():
                    final_response = final_response.replace(ph, orig)
                for ph, orig in preserved_map.items():
                    final_response = final_response.replace(ph, orig)

            # Ensure ticket id appears in the response header if missing
            if ticket_id and ticket_id not in final_response:
                final_response = _inject_ticket_into_response(final_response, ticket_id)
                if ticket_id not in final_response:
                    final_response = f"Ticket: {ticket_id}\n\n" + final_response

            return final_response

    return RAGPipeline()

def initialize_all_pipelines():
    with ThreadPoolExecutor() as executor:
        kb_future = executor.submit(initialize_kb_rag_pipeline)
        sla_future = executor.submit(initialize_sla_rag_pipeline)
        kb_pipeline = kb_future.result()
        sla_pipeline = sla_future.result()
    return kb_pipeline, sla_pipeline
