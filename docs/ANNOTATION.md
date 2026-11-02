# Independent annotation rubric

Work on a copy of `data/human_review.csv`, stored in `local/`. Preserve `review_id` and `text`. Label before inspecting predictions. The template hides UCI sentiment labels to reduce anchoring. Do not ask the classifier or another LLM to fill reference labels. Record the annotator's name/initials and set `annotation_status=reviewed` only after completing all fields. Leave ambiguous examples pending with notes rather than guessing.

Choose a single primary theme:

| Label | Definition |
|---|---|
| product_quality | Food/product taste, quality, condition, temperature |
| service | Staff behavior, support, treatment |
| speed | Waiting time, delays, delivery timing |
| price | Value, charges, refunds |
| other | No clear theme or outside the taxonomy |

For multiple themes, choose the most explicit problem; for equally explicit problems choose the highest severity, then the first mentioned. Record secondary issues in notes. Positive reviews also receive a theme.

| Severity | Definition |
|---|---|
| 0 | No reported problem, including positive or purely descriptive feedback |
| 1 | Minor inconvenience or dissatisfaction with limited explicit consequence |
| 2 | Material failure: unusable product, missing service, substantial delay, loss explicitly described |
| 3 | Explicit safety harm or fraud allegation; classify the claim, never assume it is verified |

Copy one exact contiguous quote into `evidence_gold`. It must support the theme and reported severity. Do not translate or rewrite the quote. If evidence cannot support the chosen labels, revise the labels or leave the row pending. A long quote is allowed if necessary.

UCI supplies independent positive/negative sentiment labels in the separate evaluation file. Those labels do not establish neutral/mixed classification, themes or severity. Keep original reference sentiment intact. Note suspected source-label errors in a separate adjudication file; do not silently alter references after seeing predictions.

For a stronger study, ask two people to independently label the same subset; compare agreement (theme Cohen's kappa, severity weighted kappa) and resolve disagreements with a written rationale. This is planned work, not a completed result. UI corrections are useful operational feedback but must not automatically become an independent benchmark.
