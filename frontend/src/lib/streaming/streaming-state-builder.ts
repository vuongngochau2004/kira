/**
 * StreamingStateBuilder - Build complete message state from SSE chunks
 *
 * Design principles:
 * - State Machine pattern for clear state transitions
 * - Immutable state updates
 * - Single Responsibility: Only build state, not parse or render
 * - Type-safe state representation
 */

import { createStreamingParser, type ParseState } from './thinking-tag-parser'

// ==================== Types ====================

export type StreamingState = 'connecting' | 'routing' | 'retrieving' | 'generating' | 'complete' | 'error'

export interface RoutingInfo {
  router: string
  intent?: string
}

export interface RetrievalStage {
  iteration: number
  strategy: 'dense' | 'hybrid'
  docsRetrieved: number
}

export interface SourceChunk {
  id: string
  chunk_id?: string
  content: string
  score: number
  document_id?: string
  chunk_index?: number
}

/**
 * Complete message state after processing all chunks
 */
export interface MessageState {
  /** Current streaming state */
  status: StreamingState
  /** Routing information */
  routing: RoutingInfo | null
  /** Retrieval stages */
  retrieval: RetrievalStage[]
  /** Reasoning content (from <thinking> tags) */
  reasoning: string
  /** Main response content */
  content: string
  /** Source citations */
  sources: SourceChunk[]
  /** Error message if any */
  error: string | null
  /** Timestamp of state update */
  timestamp: number
}

/**
 * Internal builder state (not exposed to consumers)
 */
interface BuilderState extends MessageState {
  /** Thinking tag parser state */
  parserState: ParseState
  /** Has retrieval completed? */
  retrievalComplete: boolean
}

// ==================== Constants ====================

/** Maximum number of retrieval stages to prevent unbounded growth */
const MAX_RETRIEVAL_STAGES = 50

/** Maximum reasoning content length (chars) to prevent memory issues */
const MAX_REASONING_LENGTH = 50000

const INITIAL_STATE: BuilderState = {
  status: 'connecting',
  routing: null,
  retrieval: [],
  reasoning: '',
  content: '',
  sources: [],
  error: null,
  timestamp: Date.now(),
  parserState: {
    isInThinkingTag: false,
    reasoning: '',
    content: '',
  },
  retrievalComplete: false,
}

// ==================== StreamingStateBuilder ====================

/**
 * State builder for accumulating streaming chunks into complete message state
 *
 * Usage:
 * ```ts
 * const builder = new StreamingStateBuilder()
 *
 * for await (const chunk of stream) {
 *   builder.processChunk(chunk.type, chunk.data)
 *   const state = builder.getState()
 *   // Use state for rendering
 * }
 *
 * const final = builder.finalize()
 * ```
 */
export class StreamingStateBuilder {
  private state: BuilderState = { ...INITIAL_STATE }
  private parser = createStreamingParser()

  /**
   * Process a single SSE chunk and update state
   */
  processChunk(type: string, data: any): void {
    this.state.timestamp = Date.now()

    // DEBUG: Log all chunk types received
    console.log('[StreamingStateBuilder] Chunk received:', {
      type,
      dataLength: data?.text ? data.text.length : 0,
      dataPreview: data?.text ? data.text.substring(0, 50) + '...' : 'N/A'
    })

    switch (type) {
      case 'routing':
        this.processRouting(data)
        break

      case 'retrieval':
        this.processRetrieval(data)
        break

      case 'content':
        this.processContent(data)
        break

      case 'thinking':
        this.processThinking(data)
        break

      case 'metadata':
        this.processMetadata(data)
        break

      case 'done':
        this.processDone()
        break

      case 'error':
        this.processError(data)
        break

      default:
        console.warn(`[StreamingStateBuilder] Unknown chunk type: ${type}`)
    }
  }

  /**
   * Get current immutable state snapshot
   */
  getState(): MessageState {
    return {
      status: this.state.status,
      routing: this.state.routing,
      retrieval: [...this.state.retrieval],
      reasoning: this.state.reasoning,
      content: this.state.content,
      sources: [...this.state.sources],
      error: this.state.error,
      timestamp: this.state.timestamp,
    }
  }

  /**
   * Finalize and get complete state
   * Called when streaming is complete
   */
  finalize(): MessageState {
    const final = this.getState()

    // Ensure proper final state
    if (final.status === 'error') {
      return final
    }

    return {
      ...final,
      status: 'complete',
    }
  }

  /**
   * Reset builder for new message
   */
  reset(): void {
    this.state = { ...INITIAL_STATE }
    this.parser.reset()
  }

  // ==================== Private Methods ====================

  private processRouting(data: any): void {
    this.state.status = 'routing'

    if (data?.router) {
      this.state.routing = {
        router: data.router,
        intent: data.intent,
      }
    }
  }

  private processRetrieval(data: any): void {
    this.state.status = 'retrieving'

    const iteration = data?.iteration ?? 1
    const strategy = data?.strategy ?? 'hybrid'
    const docsRetrieved = data?.docs_retrieved ?? 0

    // Prevent unbounded growth - limit retrieval stages
    if (this.state.retrieval.length < MAX_RETRIEVAL_STAGES) {
      this.state.retrieval.push({
        iteration,
        strategy: strategy.toLowerCase() === 'hybrid' ? 'hybrid' : 'dense',
        docsRetrieved,
      })
    } else {
      console.warn(`[StreamingStateBuilder] Max retrieval stages (${MAX_RETRIEVAL_STAGES}) reached, skipping additional entries`)
    }
  }

  private processContent(data: any): void {
    this.state.status = 'generating'

    const text = data?.text ?? ''
    if (!text) return

    // Use parser to handle thinking tags
    const parserResult = this.parser.feed(text)

    // CRITICAL FIX: Update BOTH content and reasoning from parser during streaming
    // This allows thinking content (from <thinking> tags) to be displayed in real-time
    this.state.content = parserResult.content
    this.state.reasoning = parserResult.reasoning
    this.state.parserState = parserResult  // Update parser state as well
  }

  private processThinking(data: any): void {
    this.state.status = 'generating'

    const text = data?.text ?? ''
    if (!text) return

    // DEBUG: Log when thinking content is received
    console.log('[StreamingStateBuilder] Thinking chunk received:', {
      length: text.length,
      preview: text.substring(0, 50) + '...',
      totalReasoningSoFar: this.state.reasoning.length
    })

    // Prevent unbounded growth - limit reasoning content length
    if (this.state.reasoning.length < MAX_REASONING_LENGTH) {
      this.state.reasoning += text
    } else {
      console.warn(`[StreamingStateBuilder] Max reasoning length (${MAX_REASONING_LENGTH}) reached, truncating additional content`)
    }
  }

  private processMetadata(data: any): void {
    // Sources may be in different fields
    if (data?.citations) {
      this.state.sources = data.citations
    } else if (data?.sources) {
      this.state.sources = data.sources
    }
  }

  private processDone(): void {
    this.state.status = 'complete'

    // Finalize parser state
    const finalParserState = this.parser.finalize()
    this.state.reasoning = finalParserState.reasoning
    this.state.content = finalParserState.content
  }

  private processError(data: any): void {
    this.state.status = 'error'
    this.state.error = data?.error ?? 'Unknown error'
  }
}

// ==================== Factory Function ====================

/**
 * Create a new streaming state builder
 * Convenience function for cleaner code
 */
export function createStreamingStateBuilder(): StreamingStateBuilder {
  return new StreamingStateBuilder()
}
