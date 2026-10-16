# Legal QA Golden Dataset

The legal QA benchmark checks that answers use the law **in force on the date the question is about**
and cite the right provisions. Format: `src/modules/evaluation/domain/legal_dataset.py`;
example: `docs/examples/evaluation/legal_golden_example.json` (fictional document numbers).

## Writing samples

Each sample is written against the corpus actually published in KIRA:

| Field | Meaning |
|---|---|
| `today` | The date the question is asked; the runner pins "today" to it, so answers are reproducible. |
| `category` | `current`, `past`, `compare`, `guide` or `no_answer`. |
| `expected_mode` / `expected_dates` | What the temporal resolver should produce (`single` + 1 date, or `compare` + 2 increasing dates). |
| `expected_provisions` | Provision keys (`<number>#D<article>[.K<clause>[.<point>]]`) the answer must cite; add `valid_from` to require one specific version. |
| `should_refuse` | `true` only for `no_answer`: no provision in the corpus answers the question. |

Targets (spec §9): at least 50 samples and at least 5 per category, including questions comparing the law
before and after 2026-07-01 and questions that need a guiding decree or circular.

## Checking and running

    python scripts/validate_legal_eval_dataset.py dataset/legal/golden.json
    make eval-legal DATASET=dataset/legal/golden.json

The run needs the legal corpus in Qdrant and Neo4j, the embedding API and the LLM (`LEGAL_ENABLED=true`
services). Reports go to `reports/evaluation/`.

## Metrics

- `legal_temporal_dates` — resolved mode and dates equal the expected ones.
- `legal_temporal_correctness` — every cited version is in force on the **expected** date it is used for
  (compare: `before`/`removed` at the first date, `after`/`added` at the second), so a wrong resolved
  date also shows up here.
- `legal_citation_exactness` — F1 between the expected provisions (and pinned versions) and the sources the
  answer actually cites with `[n]` markers; a no-answer sample scores 1 only when nothing is cited.
- `refusal_correctness` — no-answer samples must say that no provision was found.
- DeepEval `faithfulness` (on every source given to the LLM) and `answer_relevancy` (skipped for no-answer samples).

"Cited" means referenced by an `[n]` marker in the answer; sources the LLM received but did not cite do not
count. Pin `valid_from` for `past` and `compare` samples so the exact version is checked. Provision keys must
match the indexed granularity (an expected `D3.K1` does not match a cited `D3` or `D3.K1.a`).
