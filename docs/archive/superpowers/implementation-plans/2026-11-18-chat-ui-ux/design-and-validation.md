# KIRA conversation workspace: design and validation

Date: 2026-11-18. This document records the implementation decisions for the plan in this directory.

## Current workflow and ownership

| Task | Entry point | State owner | Visible result |
|---|---|---|---|
| Upload and processing | `/uploads`; conversation header links to it at every width | `useDocumentsUpload` | Upload, processing, completed, failed, and cancel controls on the uploads route |
| Conversation history | `CollapsibleSidebar` on desktop, `MobileNav` on mobile | Conversation store | Conversation navigation |
| Question, Stop, retry | Conversation composer | `useSimpleChat` | Streaming labels, Stop action, error banner, retry action |
| Source inspection | Conversation header and final citation | `useSourcesStore` | One `components/sources/SourcePanel` instance in the layout |
| Source preview | Selected source group | Source panel local preview state | Authorized document preview dialog |

The previous conversation tree also mounted `components/streaming/SourcePanel` and `CitationPanel` from `SimpleChat`. The chat now sends citation selection to `useSourcesStore`; only the layout mounts a source panel. The two older components remain in the repository for other callers until their imports are independently audited.

## Reference evidence

These are product documentation observations, not claims that the referenced code was copied or quality tested.

| Reference | Observed interaction | KIRA decision |
|---|---|---|
| [RAGFlow quickstart](https://ragflow.io/docs) | Users verify parsing completion before asking, then open a citation to inspect supporting content. | Keep document status visible on `/uploads` and make final citations open the selected chunk. |
| [AnythingLLM document guide](https://docs.anythingllm.com/chatting-with-documents/introduction) | Documents are scoped to workspaces and threads. | Keep KIRA source state scoped to the current conversation. |
| [Open WebUI RAG guide](https://docs.openwebui.com/features/chat-conversations/rag/) | Chat files and knowledge can produce citations for inspecting retrieved context. | Keep a source action beside the conversation and per-answer citation actions. |
| [Dify repository](https://github.com/langgenius/dify) | Public repository describes knowledge and RAG workflows. | No Dify interaction or asset was adopted without a narrower UI observation. |

Asset register: the compact source row in `frontend/src/components/sources/components/SourceSummary.tsx` is adapted from [AnythingLLM SourceItem at revision 64b599f](https://github.com/Mintplex-Labs/anything-llm/blob/64b599fc92a9c2f4d60f2f9244d278acfff73204/frontend/src/components/WorkspaceChat/ChatContainer/SourcesSidebar/SourceItem/index.jsx). The stacked source badge in `frontend/src/components/streaming/SourceCitation.tsx` is adapted from [AnythingLLM Citations at the same revision](https://github.com/Mintplex-Labs/anything-llm/blob/64b599fc92a9c2f4d60f2f9244d278acfff73204/frontend/src/components/WorkspaceChat/ChatContainer/ChatHistory/Citation/index.jsx). The source is under the [MIT License](https://github.com/Mintplex-Labs/anything-llm/blob/64b599fc92a9c2f4d60f2f9244d278acfff73204/LICENSE), reproduced at `frontend/third_party/anything-llm-LICENSE`. The adaptations use KIRA's source types, Lucide icons, theme tokens, typed props, and final-answer citation policy. No external image, logo, or font was copied. The mobile source detail remains KIRA's existing component.

## Layout and state specification

```text
Desktop (>= 1024px)
┌───────────────┬─────────────────────────────────┬──────────────────┐
│ conversations │ header: documents / sources     │ selected sources │
│               │ messages and stream status      │ and preview      │
│               │ composer / Stop                  │                  │
└───────────────┴─────────────────────────────────┴──────────────────┘

Mobile and tablet (< 1024px)
┌─────────────────────────────────┐
│ header: documents / sources     │
│ messages and stream status      │
│ composer / Stop                 │
│ bottom navigation               │
└─────────────────────────────────┘
Sources open in a focus-managed dialog; Escape and Close return focus to the trigger.
```

Use existing background, card, border, primary, muted, and destructive tokens. The source panel opens at 420px on desktop with a 340–760px resize range; mobile width is capped at the viewport. The conversation header is 56px high. Focus indicators use the primary token. Long filenames wrap in source cards and truncate in document lists.

| Answer state | Copy or affordance |
|---|---|
| Connecting/routing/retrieving/generating | Existing stage-specific status text with `role=status` |
| Provisional | “Đang kiểm tra câu trả lời · Bản nháp có thể thay đổi”; citations are inactive |
| Final | Final answer and available citation markers |
| Stopped/unsaved | “Đã dừng. Bản nháp chưa được lưu.” |
| Failure | Alert with retry when supported |
| Missing citation | “Nguồn không còn khả dụng”; no clickable source |

## Validation record

- `npm run lint`: passed.
- `npx tsc --noEmit`: passed.
- `npm test`: 80 tests passed after the AnythingLLM source UI adaptation; the full suite reports an existing controlled-input warning in `LegalUploadForm.test.tsx`.
- Focused citation and chat tests: four tests passed, covering exact chunk selection, missing source, final source opening, and provisional source suppression.
- An isolated browser session used the evaluation credentials declared in `scripts/monitor_ingestion.py`. The account was absent from the local database, so it was created through the registration UI. Credentials are not recorded here.
- At 1440px, 768px, and 375px, authenticated conversation navigation, document entry, composer visibility, and the source panel were checked. The 375px source dialog opened, closed, and returned focus to the source trigger. The desktop source trigger initially overlapped the header action; the duplicate layout trigger was removed and the panel was checked again.
- A synthetic 208-byte TXT fixture was uploaded through the browser. The UI showed upload activity, then a completed document with one indexed chunk and a displayed completion time of 0.7 seconds. This is one observed run, not a performance baseline.
- A greeting and a document question both reached a final answer. The document question displayed a 11.5-second pipeline duration, but retrieval reported zero documents and the final answer declined for insufficient evidence. Exact citation navigation therefore remains unverified in a real browser flow; component tests cover the typed citation selection path.
- The backend dev process later stopped. A subsequent document-list refresh showed “API Error” and the preview could not be validated. This was observed after the service became unavailable.

Screenshots: [desktop source panel](screenshots/desktop-sources.png), [tablet conversation](screenshots/tablet-conversation.png), [mobile answer](screenshots/mobile-answer.png), [mobile source dialog](screenshots/mobile-sources.png), and [mobile documents](screenshots/mobile-documents.png). All content is from the synthetic evaluation account. The adapted AnythingLLM elements were also checked in a temporary browser fixture with synthetic sources: [desktop](screenshots/adapted-source-desktop.png) and [mobile](screenshots/adapted-source-mobile.png). The fixture route was removed after inspection.

## Remaining task checks

Resolve why retrieval returned zero results for the completed synthetic document, then repeat the exact citation-to-source browser check. Run delayed-provider Stop/retry and session-expiry walkthroughs, and compare status and first-token timings against a controlled baseline. Keep all fixture content free of real user data.
