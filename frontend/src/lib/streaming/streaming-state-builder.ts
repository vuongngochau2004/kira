/**
 * StreamingStateBuilder - Simple, clear accumulation of streaming chunks
 *
 * Design: Just accumulate data, don't parse or transform
 * - Each chunk type has its own accumulator
 * - Clear separation of concerns
 */

// ==================== Types ====================

export type StreamingState = 'connecting' | 'routing' | 'retrieving' | 'generating' | 'complete' | 'error'

export interface RoutingInfo {
  router: string
  intent?: string
}

export interface RetrievalStage {
  iteration: number
  strategy: 'dense' | 'hybrid'
  chunksRetrieved: number      // Number of chunks retrieved
  uniqueDocuments: number      // Number of unique documents
  topDocuments?: string[]      // Top document IDs (max 3)
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
  /** Thinking/reasoning content (from 'thinking' chunks) */
  thinking: string
  /** Main response content (from 'content' chunks) */
  content: string
  /** Source citations */
  sources: SourceChunk[]
  /** Error message if any */
  error: string | null
  /** Timestamp of last update */
  timestamp: number
}

// ==================== Constants ====================

const INITIAL_STATE: MessageState = {
  status: 'connecting',
  routing: null,
  retrieval: [],
  thinking: '',
  content: '',
  sources: [],
  error: null,
  timestamp: Date.now(),
}

// ==================== StreamingStateBuilder ====================

export class StreamingStateBuilder {
  private state: MessageState = { ...INITIAL_STATE }

  /**
   * Process a single SSE chunk and update state
   */
  processChunk(type: string, data: any): void {
    this.state.timestamp = Date.now()

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
        console.log(`[StreamingStateBuilder] Unknown chunk type: ${type}`)
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
      thinking: this.state.thinking,
      content: this.state.content,
      sources: [...this.state.sources],
      error: this.state.error,
      timestamp: this.state.timestamp,
    }
  }

  /**
   * Finalize and get complete state
   */
  finalize(): MessageState {
    return {
      ...this.getState(),
      status: 'complete',
    }
  }

  /**
   * Reset builder for new message
   */
  reset(): void {
    this.state = { ...INITIAL_STATE }
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
    // Support both old (docs_retrieved) and new (chunks_retrieved) field names
    const chunksRetrieved = data?.chunks_retrieved ?? data?.docs_retrieved ?? 0
    const uniqueDocuments = data?.unique_documents ?? 1
    const topDocuments = data?.top_documents ?? []

    this.state.retrieval.push({
      iteration,
      strategy: strategy.toLowerCase() === 'hybrid' ? 'hybrid' : 'dense',
      chunksRetrieved,
      uniqueDocuments,
      topDocuments,
    })
  }

  private processContent(data: any): void {
    this.state.status = 'generating'

    const text = data?.text ?? ''
    if (text) {
      this.state.content += text
    }
  }

  private processThinking(data: any): void {
    this.state.status = 'generating'

    const text = data?.text ?? ''
    if (text) {
      this.state.thinking += text
    }
  }

  private processMetadata(data: any): void {
    this.state.status = 'generating'

    if (data?.citations) {
      this.state.sources = data.citations
    } else if (data?.sources) {
      this.state.sources = data.sources
    }
  }

  private processDone(): void {
    this.state.status = 'complete'
  }

  private processError(data: any): void {
    this.state.status = 'error'
    this.state.error = data?.error ?? 'Unknown error'
  }
}

// ==================== Factory Function ====================

export function createStreamingStateBuilder(): StreamingStateBuilder {
  return new StreamingStateBuilder()
}
