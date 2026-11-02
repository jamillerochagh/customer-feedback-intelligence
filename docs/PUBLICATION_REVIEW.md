# Review before public repository release

Date: November 2, 2026 (America/Sao_Paulo).

## Scope and findings

- Reviewed every file in the initial Git history and the candidate working tree using local patterns for OpenAI keys, GitHub tokens, AWS access keys, private keys, populated secret environment assignments, local home paths, and email addresses in file contents. No matches remained after correcting the scanner to distinguish a blank environment assignment from the following line. This is a bounded pattern scan, not a guarantee that every possible secret format can be detected.
- Confirmed that no `.env`, virtual environment, SQLite database, private upload, or completed human annotation is tracked. Git author name and email remain part of standard commit metadata; history was not rewritten.
- The demonstration screenshot was visually reviewed: it shows public sample data and keyword-baseline processing, with no credentials or private customer uploads.
- Rechecked the [UCI dataset page](https://archive.ics.uci.edu/dataset/331/sentiment+labelled+sentences), which states CC BY 4.0. All three bundled CSV hashes match `data/provenance.json`. Added a dedicated [data attribution notice](../data/README.md) covering source-derived examples and the screenshot.
- Reviewed ingestion, provider validation and failure handling, SQL queries, human corrections, exports, evaluation and local server settings. Values passed into SQLite queries are parameterized. The LLM has no tools or executable actions. Real-model behavior remains untested.

## Changes

- Fixed a CSV formula-protection bypass: displayed tables now use the same escaping as explicit CSV exports, protecting Streamlit's built-in table downloads as well. Original review views, JSON and SQLite retain the original text.
- Expanded ignore rules to cover `.env` variants, `.db` databases, common private-key file extensions and existing local artifacts, while keeping the empty `.env.example` available.
- Rewrote the README introduction around the product workflow, added clone instructions and the existing baseline screenshot, and separated available features from pending evaluations. Removed obsolete statements about the source never having been published and an unsupported Python compatibility recommendation.
- Preserved the measured baseline report unchanged. No real LLM performance or business impact was added to the claims.

## Validation

- `python -m pytest -q`: **25 passed**, including a new regression check for formula-safe table data that does not mutate originals.
- `python -m pip check`: no broken dependency requirements. This checks package consistency, not a vulnerability database.
- `git diff --check`: passed.
- Checked ignore behavior for `.env`, `.env.local`, `.env.production`, local SQLite files, `.db`, `.key`, and the virtual environment. `.env.example` remains includable.

## Remaining limits

No dependency vulnerability audit, external penetration test or real API execution was performed. Independent theme/severity annotation and real LLM evaluation remain pending. Public source visibility does not deploy the application or expose its ignored local data. No software license was added as part of this review; the dataset's CC BY 4.0 notice applies to source-derived data, not to the application code.
