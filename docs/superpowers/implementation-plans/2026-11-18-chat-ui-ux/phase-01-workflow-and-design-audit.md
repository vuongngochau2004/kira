# Phase 01 — Audit workflows and specify the design

## Context links

- [Parent plan](plan.md); [Plan 1](../2026-11-18-rag-streaming-and-cancellation/plan.md)
- [Conversation page](../../../../frontend/src/app/conversation/page.tsx); [layout](../../../../frontend/src/app/conversation/layout.tsx); [chat](../../../../frontend/src/components/simple/SimpleChat.tsx)

## Overview

- Date: 2026-11-18; priority: P1; implementation: pending; review: pending; dependency: Plan 1 contract.

## Key insights

The current workspace has multiple source-panel components and breakpoint-dependent document access. A visual refresh alone cannot fix unclear state transitions or hidden actions. The user specifically prefers a smoother workflow before formal evaluation, so task-based observations are the useful early check.

## Requirements

1. Inventory routes, panels, hooks, responsive breakpoints, and state ownership for upload, conversation list, chat, sources, and error states.
2. Walk five tasks: first upload, processing wait, first answer, cited follow-up, and Stop/retry. Capture desktop and mobile screenshots, interaction count, dead ends, and accessibility issues.
3. Inspect the corresponding workflows in the four reference projects' public UI/docs or running demos. Record observed behavior and source link; distinguish code-confirmed behavior from screenshots or product claims.
4. Produce a KIRA-specific wireframe, component map, token set (spacing, typography, colors, states), and acceptance checklist. Include provisional/final/rejected/unsaved answer treatments.
5. Review licenses and asset provenance before any code or visual asset is copied. Prefer original components using existing Radix/Tailwind primitives.

## Architecture

One conversation workspace owns document selection and source selection. Chat state remains in the established hook/store; query and server state remain in TanStack Query where already used. The design spec defines desktop columns and mobile drawers/sheets, including focus return and scroll behavior. Avoid a new global store until state ownership is proven to require one.

## Related code files

`frontend/src/app/conversation/{page,layout}.tsx`, `frontend/src/components/simple/{SimpleChat,DocumentPanel}.tsx`, `frontend/src/components/{sources,streaming}/SourcePanel.tsx`, `frontend/src/lib/hooks/use-simple-chat.ts`, `frontend/src/components/ui/`.

## Implementation steps

1. Trace the current render tree and event ownership; mark unused components only after reference search.
2. Capture baseline task walkthroughs at 375px, 768px, and desktop widths with realistic processing, error, and long-response states.
3. Compare reference products on navigation, upload feedback, source inspection, streaming affordance, and mobile handling. Create a short evidence ledger with repository/doc links and inspection date.
4. Draw and review low-fidelity layouts and state diagrams; define copy for processing, provisional, final, stopped, and failed states.
5. Write a small design specification and component migration map; identify every reused external asset and its license or choose an original substitute.

## Todo list

- [ ] Current-state inventory and baseline screenshots.
- [ ] Reference-flow evidence ledger and asset/license register.
- [ ] Desktop/mobile wireframes and state/copy specification.
- [ ] Component ownership map and phase acceptance checklist.

## Success criteria

Every existing chat/document/source component has an owner or planned removal, and each important state has a visible design. A reviewer can use the wireframe to walk all five tasks without relying on an unlabelled desktop-only panel.

## Risk assessment

Reference products may optimize for different users and datasets. Adopt only interactions that serve KIRA's authenticated personal-document workflow; avoid importing their whole information architecture.

## Security considerations

Do not expose document titles, excerpts, or source previews before authorization. External screenshots and copied assets must contain no real user data.

## Next steps

Implement the agreed component map in [Phase 02](phase-02-responsive-workspace.md).
