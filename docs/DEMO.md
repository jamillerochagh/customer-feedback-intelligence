# Three-minute demonstration

**0:00 — Problem.** “Reading review summaries is easy; checking whether they are supported is harder. This tool connects each classification and investigation priority to its original review.”

**0:25 — Ingestion.** Start with the public sample and its default 30-review cap, show text mapping and the ingestion report. Explain exact text identities and duplicate handling. If no API key is configured, explicitly say: “This run uses a local keyword baseline, not an LLM.” With a configured key, select OpenAI and reduce the cap to 5–20 reviews before Analyze.

**0:55 — Evidence.** Filter a theme or sentiment, open an original review, and compare its literal quote to the classification. Explain that quote validation catches fabrication but not every interpretation error.

**1:25 — Reliability.** Click Analyze again to show cached results. Inspect configuration and attempt audit. Explain safe per-row errors and bounded retry. Do not manufacture API failures in the live demo or claim mocks are real API behavior.

**1:50 — Decisions.** Show priority score, frequency and evidence IDs. Explain that the tool ranks reported problems; it does not prove root causes. Select an action hypothesis and describe manual verification plus an experiment or comparable-window metric.

**2:15 — Review and export.** Save one human correction with reason, show preserved machine output in JSON, and export results. Explain the distinction between operational review and independent evaluation.

**2:40 — Evaluation.** Open the recorded baseline report. State its sample size, metrics, abstention and limitations. Show the blank human annotation template and pending LLM run. Close with what evidence is needed before any stronger claim.

# Technical interview talking points

- **Why Streamlit and SQLite?** One process and one local user allow a complete vertical slice without a separate API or deployment. FastAPI becomes useful when multiple clients or independent services actually need it.
- **Why a provider interface?** Extraction depends on a small validated contract. Provider-specific authentication and parsing stay behind one adapter.
- **Why structured output and local validation?** Syntax/type correctness and evidence provenance can be checked deterministically. Semantic correctness requires external labels and human review.
- **What prevents repeated cost?** Successful results are cached by exact text and full extraction configuration. Transient failures can still be billed and repeated; local cache is not exactly-once API delivery.
- **What is independently measured?** The versioned baseline run uses original UCI sentiment labels on 60 held-out sentences. Theme/severity require independent annotations. A real LLM comparison remains pending until API execution.
- **Where can it fail?** Negation, sarcasm, multiple issues, out-of-domain language, misleading quotes, prompt injection and biased samples. Review flags are heuristics, not a guarantee of error detection.
- **How would it reach production?** First measure errors and cost; then add authentication, retention controls, transactional job claiming and observable workers if real usage requires them. Avoid claiming production readiness now.
