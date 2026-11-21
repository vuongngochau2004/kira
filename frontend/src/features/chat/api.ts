/** Chat API: SSE streaming client, chat completions and conversations. */
import { API_BASE, ApiError, fetchAPI } from '@/lib/api/http'
import { z } from 'zod'

export interface ChatResponse {
  answer: string
  model: string
  provider: string
  conversation_id?: string
}

export interface SSEChunk {
  type: 'routing' | 'retrieval' | 'content' | 'content_replace' | 'thinking' | 'status' | 'metadata' | 'done' | 'error'
  data: unknown
}

const sseChunkSchema = z.object({
  type: z.enum(['routing', 'retrieval', 'content', 'content_replace', 'thinking', 'status', 'metadata', 'done', 'error']),
  data: z.unknown().optional(),
})

const answerChunkSchema = z.object({
  text: z.string(),
  provisional: z.boolean().optional(),
  attempt: z.number().int().positive().optional(),
})

export interface RoutingData {
  router: string
  intent?: string
  confidence?: number
}

export interface RetrievalData {
  iteration: number
  strategy: string
  chunks_retrieved?: number  // New field name
  unique_documents?: number  // New field
  top_documents?: string[]   // New field
  docs_retrieved?: number   // Deprecated: legacy field name
}

export interface ContentData {
  text: string
}

export interface MetadataData {
  citations?: Array<Record<string, unknown>>
  attachments?: Array<Record<string, unknown>>
  conversation_id?: string
  message_id?: string
}

export interface ErrorData {
  error: string
}

// ==================== SSE Streaming Client ====================

/**
 * SSE Client for real-time chat streaming
 * Handles connection, parsing, and error recovery
 */
export class SSEClient {
  private controller: AbortController | null = null
  private reader: ReadableStreamDefaultReader<Uint8Array> | null = null
  private decoder = new TextDecoder()
  private buffer = ''

  /**
   * Connect to SSE stream and yield chunks
   */
  async *stream(
    endpoint: string,
    body: unknown,
    signal?: AbortSignal
  ): AsyncGenerator<SSEChunk, void, unknown> {
    this.controller = new AbortController()
    const requestSignal = signal || this.controller.signal

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
        signal: requestSignal,
        credentials: 'include',
      })

      if (!response.ok) {
        let errorMessage = 'Stream connection failed'
        try {
          const cloned = response.clone()
          const errorData = await cloned.json().catch(async () => {
            const text = await cloned.text()
            return { detail: text }
          })
          errorMessage = errorData?.error?.message || errorData?.detail || errorData?.message || errorMessage
        } catch {
          // Ignore parse errors
        }
        throw new ApiError(errorMessage, response.status)
      }

      if (!response.body) {
        throw new ApiError('Response body is null', undefined)
      }

      this.reader = response.body.getReader()

      while (true) {
        const { done, value } = await this.reader.read()

        if (done) break

        // Decode and process chunks
        this.buffer += this.decoder.decode(value, { stream: true })

        // Process complete SSE messages
        const lines = this.buffer.split('\n\n')
        this.buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.trim()) continue

          // Parse SSE format: "data: {json}"
          const match = line.match(/^data:\s*(.+)$/m)
          if (match) {
            try {
              const parsed = sseChunkSchema.safeParse(JSON.parse(match[1]))
              if (!parsed.success) continue
              if (parsed.data.type === 'content' || parsed.data.type === 'content_replace') {
                if (!answerChunkSchema.safeParse(parsed.data.data).success) continue
              }
              yield { type: parsed.data.type, data: parsed.data.data }
            } catch {
              // Ignore parse errors
            }
          }
        }
      }
    } catch (error) {
      // Ignore abort errors (user cancellation)
      if (error instanceof Error && error.name === 'AbortError') {
        return
      }
      throw error
    } finally {
      this.cleanup()
    }
  }

  /**
   * Cancel the ongoing stream
   */
  abort(): void {
    this.controller?.abort()
    this.cleanup()
  }

  private cleanup(): void {
    this.reader?.cancel().catch(() => {})
    this.reader = null
    this.controller = null
    this.buffer = ''
  }
}

/** Chat API */
export const chatAPI = {
  sendMessage: async (message: string, conversationId?: string): Promise<ChatResponse> => {
    return fetchAPI<ChatResponse>('/api/v1/chat/', {
      method: 'POST',
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
      }),
    })
  },

  /**
   * Stream chat response with SSE
   * Returns an async generator that yields chunks
   */
  streamMessage: (
    message: string,
    conversationId?: string,
    signal?: AbortSignal
  ): AsyncGenerator<SSEChunk, void, unknown> => {
    const client = new SSEClient()
    return client.stream('/api/v1/chat/stream', {
      message,
      conversation_id: conversationId,
    }, signal)
  },
}

/** Conversations API */
export interface Conversation {
  id: string
  user_id: string
  title: string | null
  source: string
  status: string
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  conversation_id: string
  role: string
  content: string
  metadata: Record<string, unknown>
  created_at: string
  sources?: Array<Record<string, unknown>>
}

export interface ConversationDetail extends Conversation {
  messages: Message[]
}

export interface ConversationListResponse {
  total: number
  page: number
  page_size: number
  items: Conversation[]
}

export const conversationsAPI = {
  list: async (page = 1, pageSize = 20, search = ''): Promise<ConversationListResponse> => {
    interface RawConversationListResponse {
      total: number
      page?: number
      page_size?: number
      limit?: number
      offset?: number
      conversations?: Conversation[]
      items?: Conversation[]
    }
    const params = new URLSearchParams({
      limit: String(pageSize),
      offset: String((page - 1) * pageSize),
    })
    if (search.trim()) params.set('search', search.trim())
    const data = await fetchAPI<RawConversationListResponse>(`/api/v1/chat/conversations?${params}`)
    return {
      total: data.total,
      page: data.page || page,
      page_size: data.page_size || data.limit || pageSize,
      items: data.conversations || data.items || [],
    }
  },

  create: (source = 'web', title?: string) =>
    fetchAPI<Conversation>('/api/v1/chat/conversations', {
      method: 'POST',
      body: JSON.stringify({ source, title }),
    }),

  get: (id: string) =>
    fetchAPI<ConversationDetail>(`/api/v1/chat/conversations/${id}`),

  update: (id: string, data: { title?: string; status?: string }) =>
    fetchAPI<Conversation>(`/api/v1/chat/conversations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchAPI(`/api/v1/chat/conversations/${id}`, { method: 'DELETE' }),
}
