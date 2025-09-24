This folder contains small troubleshooting and developer helper scripts used during
development of the RAG pipelines and SLA debugging.

Files:
- debug_search.py - quick local search against the persisted Chroma stores.
- run_sla_query.py - simple runner that demonstrates the SLA RAG pipeline end-to-end.
- token_test.py - OAuth token fetch helper for validating bot credentials.
- check_ticket_in_file.py - helpers to scan Excel files for tickets.

Usage
-----
Run these scripts from the repository root so `backend/.env` is loaded correctly:

  python .\backend\troubleshooting\run_sla_query.py

Most scripts will attempt to load `backend/.env` automatically.

Notes
-----
These helpers are intended for local debugging only. They are not part of the production
bot surface and should not be used in a deployed environment without review.
Troubleshooting scripts

This folder contains helper scripts used during development to inspect vectorstores, find tickets in source Excel files, and run quick RAG checks.

Files:
- check_ticket_in_file.py — helper to find a ticket id inside Excel rows
- debug_search.py — search persisted Chroma stores for a query and print snippets
- find_ticket_abs.py — alternative ticket search helper
- find_ticket_in_excels.py — parallel/expanded ticket search across excels
- run_sla_query.py — quick runner that calls the SLA pipeline and prints the result
- test_rag_e2e.py — end-to-end RAG test harness
- token_test.py — small tokenization/debug helper

Usage: run these from the `backend` folder (they rely on the backend venv and backend/.env). Example:

```powershell
& '.\.venv\Scripts\python.exe' '.\troubleshooting\debug_search.py' IN0042923 --k 5
```

Note: these are development helpers and not part of the production bot server. Keep them around for debugging, or remove/convert to tests as needed.
