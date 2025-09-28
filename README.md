
# On Premise RAG + Microsoft Presidio (PII) + Azure OpenAI + Chroma + Azure Bot Service (Flask)

End-to-end local starter to run a dual-pipeline **RAG** system (KB PDFs + SLA Excel) using **ChromaDB**, with **PII anonymization via Presidio**, **Azure OpenAI** for chat + embeddings, and **Bot Framework** endpoints exposed via **Flask**.

## Problem statement:
Financial services (FSI) organizations are highly regulated and often constrained from moving sensitive customer data to public cloud services. Many customers want the benefits of modern AI — smarter search, RAG, and automated support — but are not ready to fully trust cloud-hosted models or systems due to data residency, privacy, and compliance requirements. This prevents them from safely adopting Azure AI capabilities that could materially improve operations and customer experience.

## Opportunity with this accelerator:
The accelerator provides a hybrid RAG pattern that lets FSI customers safely adopt Azure AI without exposing raw PII or leaving them non-compliant. Key advantages:

Hybrid deployment: run retrieval and storage on-prem or in a controlled environment while using Azure AI for inference, meeting data residency and network policies.
Built-in anonymization: automatic PII detection and placeholder mapping ensure sensitive fields are never sent in cleartext to external models; originals can be restored in the final response where policy allows.
Compliance-first design: supports auditability, minimizes surface area for regulated data, and aligns with common controls (data minimization, encryption-in-transit/at-rest, least privilege).
Fast path to value: pre-wired RAG pipelines, vectorstore wiring and examples let teams prototype secure assistants quickly without redoing compliance plumbing.
How anonymization secures communication

Removes or replaces PII before any outbound requests, reducing the risk of leaks and limiting what must be justified by policy or contract.
Uses reversible placeholder mapping so models can reason over anonymized context while the system restores approved pieces in the final output — preserving utility without sacrificing privacy.
Enables safe sharing of contextual evidence (logs, tickets, snippets) with external LLMs while keeping the authoritative, re-identifiable data inside the customer’s control plane.
Bottom line This accelerator unlocks Azure AI for conservative, regulated FSI customers by combining hybrid deployment patterns, strong anonymization, and compliance-aware defaults — delivering AI-driven productivity while keeping regulated data protected.

## Architecture
<img width="745" height="493" alt="image" src="https://github.com/user-attachments/assets/9c6b3891-2296-4903-a133-77dca7965fe6" />



## Structure
```
.
├─ backend/
│  ├─ multiple_data_processing.py   # RAG pipelines + Presidio
│  ├─ bot_handler.py                # Bot adapters & handlers
│  ├─ main.py                       # Flask endpoints (/api/kb-bot, /api/sla-bot)
│  ├─ requirements.txt
│  └─ .env.example
├─ data/
│  ├─ kb_documents/                 # put PDFs here
│  └─ sla_tickets/                  # put .xlsx here
├─ infra/
│  ├─ Dockerfile                    # optional
│  └─ docker-compose.yml            # optional
├─ .vscode/launch.json              # VS Code debugger config
├─ .gitignore
└─ README.md
```

## Quickstart

1) Copy env and fill:
```bash
cp backend/.env.example backend/.env
```

2) Create venv, install, run:
```bash
cd backend
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
python -m pip install --upgrade pip
# Azure AI Hybrid RAG Accelerator — On‑Prem RAG + Presidio + Azure OpenAI + Chroma + Bot Framework

Lightweight end-to-end starter demonstrating a dual-pipeline Retrieval-Augmented Generation (RAG) system:

- SLA pipeline (Excel tickets) and KB pipeline (PDFs)
- ChromaDB for vector storage
- Microsoft Presidio for PII anonymization (with optional restore into final responses)
- Azure OpenAI for embeddings and chat
- Bot Framework endpoints exposed via Flask for integration (Teams or custom clients)

This README documents setup, indexing, running, testing, and troubleshooting for local development (Windows PowerShell examples included).

## Table of contents
- Overview
- Repository layout
- Prerequisites
- Environment variables (.env)
- Install (Windows PowerShell)
- Index / Rebuild vectorstores
- Run locally (Flask / bot endpoints)
- Debug and test helpers
- Configuration & toggles (PII restore, dev auth)
- Troubleshooting
- Next steps & notes

## Overview

The repository provides two RAG pipelines:

- SLA pipeline: reads Excel(s) from `data/sla_tickets/`, indexes rows, answers ticket queries (ticket IDs like `IN0042923`).
- KB pipeline: loads PDF documents from `data/kb_documents/` and answers knowledge-base questions.

Presidio anonymizes retrieved context before it is sent to the LLM. A mapping of placeholders -> original values is kept so the original PII can be restored into the final LLM response when configured.

The Flask app exposes these endpoints:

- POST `/api/sla-bot` — send a Bot Framework activity JSON for the SLA bot
- POST `/api/kb-bot` — for the KB bot
- GET `/` — health check

Pipelines are lazily initialized on first message to avoid slow server startup caused by spaCy/Presidio imports.

## Repository layout

```
.
├─ backend/
│  ├─ multiple_data_processing.py   # RAG pipelines + anonymization helpers
│  ├─ bot_handler.py                # Bot adapters & handlers (lazy pipeline init)
│  ├─ main.py                       # Flask endpoints (/api/kb-bot, /api/sla-bot)
│  ├─ debug_search.py               # helper to inspect Chroma stores
│  ├─ run_sla_query.py              # quick runner for SLA pipeline
│  ├─ requirements.txt
│  └─ .env.example
├─ data/
│  ├─ kb_documents/                 # put PDFs here
│  └─ sla_tickets/                  # put .xlsx files here
├─ infra/
│  ├─ Dockerfile                    # optional
│  └─ docker-compose.yml            # optional
├─ .gitignore
└─ README.md
```

## Prerequisites

- Python 3.10+ (3.11 used in development)
- PowerShell (Windows) or bash (macOS/Linux)
- Azure OpenAI access (endpoint, key, and deployments) for real LLM/embeddings
- If using Presidio (default), spaCy and a spaCy language model (e.g., `en_core_web_sm`)
- Optional: Docker if you prefer containerized runs

## Environment variables

Copy the example env and fill values:

```powershell
cp backend/.env.example backend/.env
```

Important variables (fill in `backend/.env` or export in your shell):

- AZURE_OPENAI_API_KEY — Azure OpenAI key
- AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_BASE — endpoint
- AZURE_OPENAI_DEPLOYMENT_NAME — chat model deployment name (e.g., gpt-4.1)
- AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME — embeddings deployment
- AZURE_OPENAI_API_VERSION — (if required)
- AZURE_OPENAI_EMBEDDINGS_MODEL_NAME — e.g., text-embedding-3-large
- SLA_BOT_APP_ID / SLA_BOT_APP_PASSWORD — Bot Framework credentials (optional for local dev)
- KB_BOT_APP_ID / KB_BOT_APP_PASSWORD
- AZURE_TENANT_ID — (optional) tenant for Bot Framework
- RESTORE_PII — true|false (default true). When true, final responses will have detected PII restored. Set `false` to keep redactions in outputs.
- DEV_BYPASS_AUTH — true|false (when true, `main.py` will accept requests without Authorization for dev testing)

Security note: Do not commit `.env` to source control. Keep API keys secret.

## Install (Windows PowerShell)

From repository root:

```powershell
cd .\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Install spaCy model for Presidio (if you plan to use anonymization):

```powershell
python -m spacy validate || python -m spacy download en_core_web_sm
# or download a larger model:
# python -m spacy download en_core_web_lg
```

If you prefer Docker, see `infra/docker-compose.yml` and `infra/Dockerfile` (optional).

## Index / Rebuild Chroma vectorstores

Vectorstores are persisted under `backend/.chroma_sla` and `backend/.chroma_kb`. Rebuild when data changes.

From project root (PowerShell):

```powershell
# remove old SLA store (if present)
Remove-Item -Recurse -Force ".\backend\.chroma_sla" -ErrorAction SilentlyContinue

# Rebuild SLA vectorstore
& '.\backend\.venv\Scripts\python.exe' -c "import sys; sys.path.insert(0, r'.\backend'); from multiple_data_processing import initialize_sla_rag_pipeline; initialize_sla_rag_pipeline()"

# Optionally rebuild KB vectorstore
Remove-Item -Recurse -Force ".\backend\.chroma_kb" -ErrorAction SilentlyContinue
& '.\backend\.venv\Scripts\python.exe' -c "import sys; sys.path.insert(0, r'.\backend'); from multiple_data_processing import initialize_kb_rag_pipeline; initialize_kb_rag_pipeline()"
```

Notes:
- Excel temp files like `~$Tickets...` may produce permission warnings — these are skipped.
- Indexing requires Azure credentials for embeddings; ensure `backend/.env` is configured or env vars are exported.

## Run locally (Flask + Bot endpoints)

Start the Flask server from the backend folder:

```powershell
cd .\backend
.\.venv\Scripts\Activate.ps1
python .\main.py
```

Or start from the repo root using the venv Python:

```powershell
& '.\backend\.venv\Scripts\python.exe' '.\backend\main.py'
```

Health check:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:3978/ -Method Get
# expected: {"status":"RAG Teams Bot is running!"}
```

Important: pipelines are lazily initialized on the first message to avoid slow startup due to spaCy/Presidio imports. The first SLA/KB request will be slower while pipelines initialize.

## Debug and test helpers

- Inspect Chroma contents for a query (useful to confirm indexing):

```powershell
& '.\backend\.venv\Scripts\python.exe' '.\backend\debug_search.py' IN0042923 --k 5
```

- Quick SLA query runner (prints the pipeline response):

```powershell
& '.\backend\.venv\Scripts\python.exe' '.\backend\run_sla_query.py'
```

## Example Bot Framework POST (dev testing)

`main.py` enforces Authorization header unless `DEV_BYPASS_AUTH=true` in `.env`. Example PowerShell request with dev bypass enabled:

```powershell
$body = @{
  type = 'message'
  text = 'Please provide more information about ticket IN0042923: last update, assigned engineer, status.'
  from = @{ id = 'u1' }
  recipient = @{ id = 'b1' }
  conversation = @{ id = 'c1' }
  id = 'm1'
  serviceUrl = 'http://localhost'
} | ConvertTo-Json

Invoke-RestMethod -Uri http://127.0.0.1:3978/api/sla-bot -Method Post -Body $body -ContentType 'application/json' -Headers @{ Authorization = 'Bearer dev' }
```

If `DEV_BYPASS_AUTH=true` and you omit Authorization header, `main.py` will synthesize a dev token for local testing.

## Configuration & toggles

- `RESTORE_PII` (default `true`): whether the application will re-insert original PII into the final LLM response. For production, consider `false` or a selective policy.
- `DEV_BYPASS_AUTH`: set to `true` for local dev to relax Authorization checks.
- `PRESIDIO_FRIENDLY_REPLACEMENTS`: toggle friendly redaction labels (default true).

## Troubleshooting

1. Server slow or hangs on startup
    - Cause: importing Presidio / spaCy at module import time is heavy. The repo defers Presidio creation and pipeline initialization by default; however, if your environment lacks spaCy model data, the first request may be slow.
    - Fix: install spaCy and a model: `python -m spacy download en_core_web_sm`.

2. Missing Azure credentials / pydantic validation errors
    - Ensure `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` (or `AZURE_OPENAI_API_BASE`) are set in `backend/.env` or exported in your shell.

3. Index rebuild returns 0 results
    - Verify Excel/PDF files are in `data/` at repo root, not in `backend`.
    - Re-run rebuild from repo root so `EXCEL_FOLDER_PATH`/`PDF_FOLDER_PATH` resolve correctly.

4. Excel temp file `~$...` permission denied
    - Normal: Excel creates lock/temp files. Loader will skip the temp file and read the real `.xlsx`.

5. Chroma deprecation warnings
    - LangChain warns that `Chroma` import will move to `langchain-chroma`. Functionality still works. Consider upgrading in the future.

6. Telemetry / capture() warnings
    - Non-blocking messages from Chroma/telemetry; safe to ignore.

## Recommended next steps (optional)

- Add a pytest integration test to assert that `sla_pipeline.run('...IN0042923...')` returns text containing `IN0042923`.
- Add a CI job to warm and smoke-test pipelines after indexing.
- Consider selective PII restoration policies (insensitive fields vs. personal names).
- Migrate to `langchain-chroma` to remove deprecation warnings.

## Quick checklist before demos

- [ ] Populate `backend/.env` with Azure/OpenAI credentials (or use local mocks).
- [ ] Put PDFs in `data/kb_documents/` and `.xlsx` in `data/sla_tickets/`.
- [ ] Create venv and install requirements.
- [ ] Rebuild the vectorstores if you added data.
- [ ] Start the server and run the health check.
- [ ] Send a POST to `/api/sla-bot` or run `run_sla_query.py` to verify output.

---

Output:
<img width="987" height="350" alt="image" src="https://github.com/user-attachments/assets/50bd8d57-1efb-4f49-9004-b98759788748" />

When asked about the ticket: the response is shown below (which is fully anonymized before calling the LLM and after retreival --> the final query is unanonymized to share the full-content with the end-user)
<img width="794" height="833" alt="image" src="https://github.com/user-attachments/assets/9cd8cb75-90c9-4f18-be5c-a1ee3abb1f49" />

