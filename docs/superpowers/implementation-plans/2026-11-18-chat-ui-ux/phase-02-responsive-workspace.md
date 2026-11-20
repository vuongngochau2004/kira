# Phase 02 — Build the responsive conversation workspace

## Context links

- [Parent plan](plan.md); [Phase 01](phase-01-workflow-and-design-audit.md)
- [Conversation layout](../../../../frontend/src/app/conversation/layout.tsx); [document panel](../../../../frontend/src/components/simple/DocumentPanel.tsx); [chat hook](../../../../frontend/src/lib/hooks/use-simple-chat.ts)

## Overview

- Date: 2026-11-18; priority: P1; implementation: pending; review: pending; dependency: Phase 01 spec.

## Key insights

Two source-panel concepts split source selection and waste screen space. A panel hidden at `xl` cannot be the only route to document management. Streaming states from Plan 1 need UI labels whose meaning survives a viewport change.

## Requirements

1. Use one source-panel implementation and one source-selection state path. Preserve cited document navigation and any existing legal source behavior.
2. Provide document access at every viewport: persistent desktop navigation and an accessible mobile sheet or route.
3. Show upload queue, extraction/embedding progress when known, completed/failed status, and recovery action. Never claim more granular progress than the backend reports.
4. Keep composer, Stop, retry, conversation switching, and long answer reading usable without scroll jumps or lost input.
5. Make provisional, final, stopped/unsaved, and error states distinct. Render citations only for final verified answer metadata.

## Architecture

Keep the conversation route as the workspace shell. Extract small typed components for navigation, conversation header, composer, document list/status, and source drawer. The chat hook remains the single owner of stream lifecycle; local panel visibility can use component state. Fetch/server cache follows existing React Query conventions. Reuse Radix Dialog/Sheet primitives and shared UI components. Explicitly map old component imports before deletion.

## Related code files

`frontend/src/app/conversation/{page,layout}.tsx`, `frontend/src/components/simple/{SimpleChat,DocumentPanel}.tsx`, `frontend/src/components/{sources,streaming}/SourcePanel.tsx`, `frontend/src/components/streaming/{PipelineTrace,CitationRichText}.tsx`, `frontend/src/lib/hooks/use-simple-chat.ts`, `frontend/src/lib/stores/`.

## Implementation steps

1. Establish typed props and shared state boundaries from the Phase 01 component map; build the shell at mobile, tablet, and desktop widths.
2. Move source selection into the sole source panel/drawer and remove duplicate rendering after parity checks. Keep valid deep-link or selected-source behavior.
3. Rework document navigation and upload status, including empty, pending, completed, failed, and permission-denied cases. Provide a mobile entry point near the conversation header.
4. Rework message and composer states around Plan 1 events: provisional preview, replacement, final citations, Stop, unsaved preview, retry. Preserve draft input when switching panels.
5. Add focused component tests for source selection, responsive actions, and each stream state; keep tests at behavior boundaries rather than snapshots of CSS.

## Todo list

- [ ] Responsive shell and mobile document/source access.
- [ ] Single source-panel component and state owner.
- [ ] Upload, message, and composer state treatments.
- [ ] Behavior-focused frontend tests.

## Success criteria

At 375px and desktop width, the five Phase 01 tasks have a visible path. The source panel never opens for a provisional citation. Switching conversation or opening a drawer preserves the draft and focus behavior. No duplicate source panel remains in the render tree.

## Risk assessment

Moving panel state may break existing source deep links or legal citation rendering. Record these paths before refactoring and include them in regression tests. Avoid broad hook rewrites while changing layout.

## Security considerations

Do not render unauthorized document metadata in navigation or source preview. Display escaped text; do not inject model-generated HTML. Abort pending fetches when the authenticated session changes.

## Next steps

Verify source interaction and accessibility in [Phase 03](phase-03-source-interaction-and-validation.md).
