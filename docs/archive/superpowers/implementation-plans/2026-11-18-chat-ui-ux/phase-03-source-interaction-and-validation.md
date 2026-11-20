# Phase 03 — Validate sources, accessibility, and task completion

## Context links

- [Parent plan](plan.md); [Phase 02](phase-02-responsive-workspace.md)
- [Citation rendering](../../../../frontend/src/components/streaming/CitationRichText.tsx); [source panel](../../../../frontend/src/components/sources/SourcePanel.tsx)

## Overview

- Date: 2026-11-18; priority: P1; implementation: pending; review: pending; dependency: Plan 3 citation binding for exact-source navigation.

## Key insights

Source links are only useful if they land on the cited page/chunk and make the evidence legible. Browser-level interaction checks reveal layout, focus, and network-state failures that component tests cannot.

## Requirements

1. Opening a final citation selects the exact available source location; missing/deleted sources show a clear fallback without leaking metadata.
2. All panels, menus, upload controls, composer actions, and feedback controls planned for Plan 5 work with keyboard and have meaningful labels, focus order, and visible focus.
3. Cover narrow/wide viewports, long filenames, long answers, empty conversation, pending upload, stream retry, cancellation, provider failure, and session expiry.
4. Measure user-visible responsiveness: time to status, first provisional token, and panel-open interaction. Compare against the Phase 01 baseline without promising a universal latency target.
5. Run repository frontend gates and browser walkthroughs with the current source build, not stale Docker images.

## Architecture

Keep source navigation as a typed event from final citation metadata to the single source panel. Lazy-load heavy preview content only when opened. Use existing UI primitives' focus management. A small browser smoke suite can script the five core tasks with fixtures; it does not attempt to score RAG answer quality.

## Related code files

`frontend/src/components/streaming/{CitationRichText,CitationPanel}.tsx`, `frontend/src/components/sources/SourcePanel.tsx`, `frontend/src/components/simple/SimpleChat.tsx`, `frontend/src/lib/hooks/use-simple-chat.ts`, frontend component and browser test locations.

## Implementation steps

1. Wire citation click to exact source ID/page/chunk from Plan 3, with unavailable-source handling.
2. Audit headings, labels, dialog focus/return, live status announcements, contrast, and reduced-motion behavior; fix defects with targeted tests.
3. Run the five task walkthroughs at 375px, 768px, and desktop, including offline/provider-error and session-expired cases. Record failures and screenshots.
4. Measure first-status/first-token timings with a delayed fake provider and compare to baseline; investigate regressions caused by rendering or source-preview loads.
5. Run `npm run lint`, `npx tsc --noEmit`, `npm test`, and browser smoke. Document remaining usability issues and ownership.

## Todo list

- [ ] Exact citation-to-source navigation and missing-source fallback.
- [ ] Accessibility audit and fixes.
- [ ] Responsive/browser task walkthroughs and timing comparison.
- [ ] Frontend gates and concise evidence report.

## Success criteria

All five core tasks complete at narrow and wide widths with keyboard access. Citation clicks reach the cited location or an explicit unavailable state. No severe focus trap, hidden action, lost draft, or misleading stream state remains in the tested flows.

## Risk assessment

The exact citation contract depends on Plan 3. If it is not implemented yet, ship only clearly labelled document-level navigation and keep exact-chunk acceptance pending; do not imply precision the backend cannot supply.

## Security considerations

Recheck ownership at source-preview/download APIs; UI filtering alone is insufficient. Avoid logging document titles or answer text in browser performance traces.

## Next steps

Place the lightweight feedback control from [Plan 5](../2026-11-18-user-feedback-loop/plan.md) on finalized assistant messages.
