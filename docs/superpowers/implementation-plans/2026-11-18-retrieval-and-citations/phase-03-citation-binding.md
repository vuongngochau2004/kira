# Phase 03 — Bind final citations to evidence

## Context links

- [Parent plan](plan.md); [Phase 02](phase-02-query-fusion-and-rerank.md)
- [Generation citations](../../../../src/modules/rag/orchestration/agents/generation_agent.py); [finalize](../../../../src/modules/rag/application/pipeline.py)
- [Chat citation enrichment](../../../../src/modules/chat/application/citations.py); [source UI](../../../../frontend/src/components/sources/SourcePanel.tsx)

## Overview

- Date: 2026-11-18; priority: P1; implementation: pending; review: pending; dependency: Phase 02.

## Key insights

Generation currently creates a citation object for every retrieved document, and finalization checks overall relevance. Neither step proves which answer sentence relies on which chunk. The source panel can show page/chunk information, so a stable source reference can be presented without a new storage system.

## Requirements

1. Give each generation context block a stable, unambiguous source marker tied to the normalized chunk key.
2. Parse final answer references against the actual retrieved candidate set. Drop unknown, duplicate, unowned, or uncited chunks from the `citations` list.
3. If a material claim lacks support, repair/reject according to the existing quality policy; never turn a guessed marker into a citation.
4. Show title, page, and excerpt for final cited chunks only; keep “related retrieved material” separate and clearly named if shown.
5. Preserve legal QA's provision/version citation contract; adapt only the personal-document path here.

## Architecture

Create a typed `EvidenceRef` mapping from context block marker to chunk provenance. Generation prompt requests stable markers. Finalizer parses markers and validates them against the mapping and owner before building public citation DTOs. Citation enrichment receives only validated IDs. The frontend opens the source panel at the cited chunk/page after final metadata; provisional text stays citation-free under Plan 1.

## Related code files

`src/modules/rag/domain/prompts/generation.py`, `src/modules/rag/orchestration/agents/generation_agent.py`, `src/modules/rag/application/{dto,pipeline}.py`, `src/modules/chat/application/citations.py`, `src/modules/chat/api/endpoints.py`, `frontend/src/components/streaming/{CitationRichText,CitationPanel}.tsx`, `frontend/src/components/sources/SourcePanel.tsx`.

## Implementation steps

1. Define marker syntax and mapping, with duplicate-page and duplicate-chunk fixtures. Ensure markers survive the final answer replacement event.
2. Validate answer references against retrieved owned chunks. Reject forged and missing IDs; normalize citation order to first appearance in the answer.
3. Keep the final evidence check bounded and keyed to referenced chunks. Make unsupported/no-reference outcomes explicit; do not silently attach all retrieved chunks.
4. Update source UI to open the exact document/page/chunk and handle a missing/deleted source gracefully.
5. Test generated text with one valid marker, multiple markers, forged marker, no marker, rejection, retry, and two-user isolation. Confirm legal citation rendering is unchanged.

## Todo list

- [ ] Define stable evidence markers and DTO.
- [ ] Validate references against owned retrieval results.
- [ ] Bind final citations and source-panel navigation.
- [ ] Add adversarial and legal-regression tests.

## Success criteria

The final citation list is exactly the valid set referenced by the answer, ordered by first use. A forged marker cannot reveal a document title or excerpt. A source click opens the cited location or a clear unavailable state. Preview tokens have no citations.

## Risk assessment

Models may omit or corrupt markers. Do not invent a match by semantic similarity. Use a clear unsupported-answer path and inspect failure counts before changing the prompt again.

## Security considerations

Validate marker-to-chunk ownership on the server, including filename enrichment and download/preview endpoints. Treat source IDs inside model output as untrusted text.

## Next steps

Expose the reliable citation interaction through [Plan 4](../2026-11-18-chat-ui-ux/plan.md).
