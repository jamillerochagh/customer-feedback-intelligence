# Public sample data and attribution

The three CSV files in this directory derive from **Sentiment Labelled Sentences**, created by **Dimitrios Kotzias (2015)** and distributed by the UCI Machine Learning Repository.

- Dataset: https://archive.ics.uci.edu/dataset/331/sentiment+labelled+sentences
- DOI: https://doi.org/10.24432/C57604
- License: **Creative Commons Attribution 4.0 International (CC BY 4.0)**, https://creativecommons.org/licenses/by/4.0/
- Associated paper: *From Group to Individual Labels Using Deep Features*, Dimitrios Kotzias, Misha Denil, Nando de Freitas and Padhraic Smyth, KDD 2015.

Changes from the source: use the Yelp restaurant-review subset; preserve the sentence text; remove exact duplicate texts; shuffle with seed 42; select 30 demonstration and 60 disjoint evaluation sentences; add exact-text SHA-256 identifiers and source-line references; map binary sentiment labels to `positive` / `negative`. No dates, ratings, theme labels, or severity labels have been invented.

`human_review.csv` is a blank annotation template for the 60 evaluation sentences. Its source-derived text remains under CC BY 4.0. Completed private annotations should be stored in the ignored `local/` directory.

The original review text reproduced in `../examples/baseline-evaluation/` and the demonstration screenshot carries the same source attribution. Machine predictions and metrics are project-generated outputs, not UCI reference labels or verified business findings. No endorsement by the dataset creators, Yelp, UCI, OpenAI, or iFood is implied.

Archive and derived-file hashes, exact archive member, and transformations are recorded in `provenance.json`. `python -m scripts.prepare_data` reproduces the split. The data license applies to the source-derived data; it does not assign a license to the application's source code.
