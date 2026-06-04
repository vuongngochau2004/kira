/**
 * Streaming module - Handles SSE streaming and thinking tag parsing
 *
 * Architecture:
 * 1. ThinkingTagParser - Pure functions for parsing <thinking> tags
 * 2. StreamingStateBuilder - State machine for building complete message state
 *
 * Design principles:
 * - Separation of concerns: Parse vs Build vs Render
 * - Pure functions where possible
 * - Immutable state updates
 * - Type-safe
 */

export {
  parseChunk,
  parseFullContent,
  stripThinkingTags,
  createStreamingParser,
  type ParseResult,
  type ParseState,
} from './thinking-tag-parser'

export {
  StreamingStateBuilder,
  createStreamingStateBuilder,
  type StreamingState,
  type MessageState,
  type RoutingInfo,
  type RetrievalStage,
  type SourceChunk,
} from './streaming-state-builder'
