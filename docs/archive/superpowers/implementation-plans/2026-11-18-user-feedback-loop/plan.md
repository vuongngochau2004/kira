---
title: "Plan 5: User feedback loop before formal RAG evaluation"
description: "Capture owner-scoped feedback on finalized answers and turn it into a reviewed improvement backlog."
status: pending
priority: P2
effort: 4-6 days
branch: develop
tags: [chat, feedback, frontend, analytics, privacy]
created: 2026-11-18
---

# Goal

Let users flag helpful and unhelpful finalized answers, optionally explain why, and use those signals to improve retrieval, citations, routing, and UI. This is a lightweight product feedback loop while KIRA lacks a representative real-world RAG dataset. It follows [Plans 1–4](../2026-11-18-chat-ui-ux/plan.md)'s stable answer identity and interface.

## Verified starting point

- The database stores conversations and messages, including message sources and metadata, but has no dedicated feedback model ([models](../../../../src/shared/infrastructure/persistence/database/models.py#L258)). A repository search found no feedback API or message-rating UI; this is an absence in the inspected tree, not proof about every deployment.
- The admin dashboard flags some answers for review using citation count and a score threshold; that is a heuristic, not explicit user feedback ([dashboard repository](../../../../src/modules/admin/infrastructure/dashboard_repository.py#L180)).
- Plan 1 persists only final assistant answers and exposes their message ID. Stopped or failed provisional previews have no durable assistant message to rate.
- `src/modules/evaluation/` contains evaluation tooling, but a representative consented dataset and measured RLHF benefit are **not verified**.

## Product decision

Start with a low-friction thumbs up/down control on saved assistant messages, optional structured reasons, and optional short comment. Use feedback for human triage and regression fixtures. Treat ratings as noisy observations, not ground truth. Do not train on private document text or automatically change prompts/models from raw feedback. RLHF or preference optimization needs explicit consent, enough high-quality paired preferences, privacy review, a fixed baseline, and an offline/online rollback plan; it is deferred.

## Phases

| Phase | Scope | Status | Effort |
|---|---|---|---|
| [01](phase-01-feedback-data-and-api.md) | Owner-scoped data model, migration, API and security tests | Pending | 1.5-2 days |
| [02](phase-02-in-chat-feedback.md) | Accessible rating and reason capture in the chat UI | Pending | 1-2 days |
| [03](phase-03-triage-and-learning-policy.md) | Admin triage, privacy controls, improvement loop and readiness criteria | Pending | 1.5-2 days |

## Acceptance

An authenticated user can submit, change, or remove one rating for their own saved assistant message. Another user cannot read or change it. Duplicate requests do not create duplicate rows. The UI never offers feedback on provisional, failed, or stopped unsaved text and recovers from API errors. Admin triage shows aggregated categories and authorized examples without silently exporting private documents. Each reviewed issue can become a reproducible fixture or a tracked product change. No automatic model training is part of this plan.

## Explicit deferrals

Defer RLHF training, reward models, public leaderboards, large-scale dataset scoring, and automatic prompt changes. Revisit formal evaluation only after the core experience is stable and feedback volume/coverage supports meaningful sampling.
