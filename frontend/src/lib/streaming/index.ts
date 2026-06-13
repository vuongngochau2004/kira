/**
 * Streaming module - Handles SSE streaming and state building
 *
 * Architecture:
 * 1. StreamingStateBuilder - State machine for building complete message state
 *
 * Design principles:
 * - Separation of concerns: Accumulate vs Render
 * - Pure functions where possible
 * - Immutable state updates
 * - Type-safe
 */

export {
  StreamingStateBuilder,
  createStreamingStateBuilder,
  ensureFlatSources,
  type StreamingState,
  type MessageState,
  type Attachment,
  type RoutingInfo,
  type RetrievalStage,
  type SourceChunk,
} from './streaming-state-builder'
