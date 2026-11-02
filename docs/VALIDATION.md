# Local validation record

Date: November 2, 2026 (America/Sao_Paulo).

Environment: Python 3.9.6, macOS ARM64, isolated `.venv`, exact installed packages in `requirements-lock.txt`.

- `python -m pytest -q`: 24 tests passed. Tests cover lossless ingestion, limits and duplicate reporting; strict output/quote validation; provider request shape; invalid JSON, invalid evidence, refusal, truncation, authentication, 429, 5xx, timeout, retry exhaustion/recovery; per-row failures, caching and configuration isolation; append-only correction behavior; formula-safe CSV; holdout separation; abstention-aware metrics; baseline UI flow and missing-key behavior.
- `python -m pip check`: no broken dependency requirements.
- `python -m scripts.evaluate --output examples/baseline-evaluation`: 60 independent source-labeled sentences; 16 correct predictions, 43 uncertain, 1 incorrect positive; zero processing failures. Accuracy 0.2667; binary macro-F1 0.4150. Full predictions, errors and attempt measurements are stored alongside the report.
- Local Streamlit server started on `127.0.0.1:8501`; health endpoint returned `ok`. Browser verification confirmed successful baseline processing and visible evidence/exploration/export controls.

Provider tests use `httpx.MockTransport` and a fake key. They verify the adapter contract and local failure handling, not real endpoint compatibility, model behavior or prompt-injection resistance. No API key was configured; no actual LLM calls were made. Theme/severity reference annotation is pending.

The application and data remain local. Nothing was pushed, deployed, shared or published. The server binds only to the loopback interface and Streamlit usage telemetry is disabled.
