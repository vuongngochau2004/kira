---
title: "Plan 4: Conversation and document UX redesign"
description: "Unify the chat workspace, improve responsive source and document workflows, and make stream states understandable."
status: pending
priority: P1
effort: 6-9 days
branch: develop
tags: [frontend, ui, chat, document, accessibility]
created: 2026-11-18
---

# Goal

Make KIRA's core workflow—upload a document, ask a question, inspect its source, and continue the conversation—clear and comfortable on desktop and mobile. Build on [Plan 1](../2026-11-18-rag-streaming-and-cancellation/plan.md)'s streaming contract and [Plan 3](../2026-11-18-retrieval-and-citations/plan.md)'s verified source references. This plan improves task completion and visual quality without introducing a second chat implementation.

## Verified starting point

- The conversation layout renders a source panel, while `SimpleChat` renders another source panel with separate state ([layout](../../../../frontend/src/app/conversation/layout.tsx#L6), [chat](../../../../frontend/src/components/simple/SimpleChat.tsx#L8)). Their roles and callers must be mapped before removal.
- `DocumentPanel` is hidden below the `xl` breakpoint ([document panel](../../../../frontend/src/components/simple/DocumentPanel.tsx)); the layout's source panel is desktop-oriented. Mobile access to documents and sources needs a real interaction path.
- The existing chat hook manages conversation, streaming, cancellation, and unsaved previews ([chat hook](../../../../frontend/src/lib/hooks/use-simple-chat.ts)). Plan 1 added explicit provisional and terminal states; the redesign must show these faithfully.
- No comparative usability study or measured task-success baseline is available. “Poor UX” is the owner's assessment, not a measured score.

## Design direction and reference policy

Use [Dify](https://github.com/langgenius/dify), [RAGFlow](https://github.com/infiniflow/ragflow), [AnythingLLM](https://github.com/Mintplex-Labs/anything-llm), and [Open WebUI](https://github.com/open-webui/open-webui) as interaction references (checked 2026-11-18). Record which interaction solves which KIRA task, then make KIRA-specific layouts and components. Copying a component requires a per-file license and attribution review. In particular, [Dify's license](https://github.com/langgenius/dify/blob/main/LICENSE) and [Open WebUI's license](https://github.com/open-webui/open-webui/blob/main/LICENSE) include frontend branding conditions; [RAGFlow](https://github.com/infiniflow/ragflow/blob/main/LICENSE) and [AnythingLLM](https://github.com/Mintplex-Labs/anything-llm/blob/master/LICENSE) have their own notice requirements. Reference links are for design research, not proof of implementation quality.

## Phases

| Phase | Scope | Status | Effort |
|---|---|---|---|
| [01](phase-01-workflow-and-design-audit.md) | Map current UX, compare reference flows, write a KIRA design spec | Pending | 1-2 days |
| [02](phase-02-responsive-workspace.md) | Build one responsive chat/document/source workspace | Pending | 3-4 days |
| [03](phase-03-source-interaction-and-validation.md) | Source interactions, accessibility, performance, browser checks | Pending | 2-3 days |

## Acceptance

A new and returning user can reach a document, identify its processing state, submit a question, distinguish provisional from final text, Stop a stream, open a final cited page/chunk, and recover from a failed upload or request. These flows work at narrow and wide viewports with keyboard and screen reader labels. No duplicated source panel or conflicting source selection state remains. Lint, TypeScript, component tests, and browser task checks pass before implementation is called complete.

## Explicit deferrals

Defer a wholesale clone of another product, a new design system package, dashboard redesign, autonomous-agent controls, and formal RAG-quality scoring. Use the small behavior fixtures from Plans 2–3 and user feedback from [Plan 5](../2026-11-18-user-feedback-loop/plan.md) to guide later changes.
