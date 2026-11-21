# Phase 03 — Triage feedback and define learning readiness

## Context links

- [Parent plan](plan.md); [Phase 02](phase-02-in-chat-feedback.md)
- [Admin dashboard repository](../../../../src/modules/admin/infrastructure/dashboard_repository.py); [evaluation module](../../../../src/modules/evaluation/)

## Overview

- Date: 2026-11-18; priority: P2; implementation: pending; review: pending; dependency: consent and feedback data from Phases 01–02.

## Key insights

Downvotes overrepresent frustrated users and do not identify a single root cause. The current dashboard's heuristic `needs_review` is not user sentiment. A human review queue can turn specific complaints into regression fixtures before a large dataset or preference-training pipeline exists.

## Requirements

1. Provide admin-only aggregate counts and a bounded, paginated review queue by reason, date, handler, and status. Clearly distinguish user feedback from heuristic review flags.
2. Show answer/context excerpts only to authorized reviewers under the existing data-access policy; avoid bulk export by default. Record reviewer actions and resolution category.
3. Define a triage rubric: routing error, retrieval miss, wrong citation, generation error, latency, UI confusion, or unclear. Link each confirmed issue to a reproducible fixture or tracked task.
4. Report feedback coverage and bias indicators (rated answers / saved answers, user distribution, handler distribution, positive/negative mix) without treating raw rating percentage as answer quality.
5. Write a readiness gate for formal evaluation and RLHF: representative consented examples, stable baseline, versioned prompts/models, privacy retention, paired preferences if training, offline holdout, and rollout/rollback plan.

## Architecture

Add admin application queries over feedback with strict pagination and aggregate SQL; reuse admin authorization. Store reviewer status and category separately from the user's original vote so user edits do not erase triage history. A small curated fixture file or test case is created only after an authorized reviewer removes private material or obtains consent. Keep analytics aggregated and avoid shipping a training pipeline here.

## Related code files

`src/modules/admin/{api,application,infrastructure}/`, `src/modules/admin/infrastructure/dashboard_repository.py`, `src/modules/chat/`, `src/modules/evaluation/`, `frontend/src/app/admin/`, `tests/`.

## Implementation steps

1. Define reviewer access, data retention, and whether answer/context excerpts may appear in admin UI. Verify current admin role checks before extending endpoints.
2. Add aggregate queries and a paginated queue with stable sorting, filters, and reviewer status. Keep user vote and reviewer classification distinct.
3. Build a concise admin view for categories, counts, coverage, and case resolution. Flag low-sample segments rather than ranking models on sparse votes.
4. Pilot a weekly review of representative negative and positive cases. Turn confirmed failures into small consented or sanitized regression fixtures assigned to Plan 2 or 3 owners.
5. Document evaluation/RLHF readiness criteria and a decision date after enough feedback exists. Run authorization, pagination, and privacy tests plus relevant backend/frontend gates.

## Todo list

- [ ] Admin authorization and retention policy.
- [ ] Bounded aggregates and review queue.
- [ ] Triage rubric, reviewer states, and UI.
- [ ] Coverage/bias report and evaluation-readiness decision document.

## Success criteria

Reviewers can identify the most common confirmed failure types without treating a raw downvote as a diagnosis. Every reviewed case has an outcome and optional linked fixture/task. Private content stays within authorized access, and a decision document states exactly what evidence is still missing before formal evaluation or RLHF.

## Risk assessment

Sparse voluntary feedback is selection-biased. Report denominator and coverage, do not use thumbs-up rate as a standalone quality score, and avoid fine-tuning on unreviewed comments. Admin queries may become expensive; paginate and index before broad rollout.

## Security considerations

Admin role checks apply to every list/detail/export path. Never export raw documents or answer text automatically. Redact or remove personal data before fixtures; honor user deletion and retention policy across review records.

## Next steps

Reassess dataset evaluation and preference training only after the readiness gate is met. Meanwhile, feed confirmed issues back into [Plan 2](../2026-11-18-agent-core-and-routing/plan.md) and [Plan 3](../2026-11-18-retrieval-and-citations/plan.md).
