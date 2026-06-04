/** Simple API client for chat, documents, and auth */

const getApiBase = () => {
  if (typeof window !== 'undefined') {
    // Client-side: use Next.js proxy rewrites to avoid CORS/network issues
    return ''
  }
  // Server-side default
  return process.env.NEXT_PUBLIC_API_URL?.replace(/\/api\/v1$/, '') || 'http://127.0.0.1:8006'
}

const API_BASE = getApiBase()

export interface ChatResponse {
  answer: string
  model: string
  provider: string
  conversation_id?: string
}

export interface Document {
  id: string
  filename: string
  file_type: string
  file_size: number
  status: 'uploading' | 'processing' | 'completed' | 'failed' | string
  error_message?: string
  created_at: string
  updated_at?: string
}

export interface AuthUser {
  id: string
  email: string
  full_name?: string
  role: string
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/** Simple fetch wrapper with auth (uses httpOnly cookies) */
async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  let response;
  try {
    response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      credentials: 'include',  // CRITICAL: Send/receive httpOnly cookies
    })
  } catch (error) {
    throw new ApiError('Network error', undefined)
  }

  if (response.status === 401) {
    // Token expired or invalid - clear auth state and redirect to login
    // Import dynamically to avoid circular dependency
    if (typeof window !== 'undefined') {
      import('@/lib/stores/auth-store').then(({ useAuthStore }) => {
        useAuthStore.getState().clearAuth()
      })
    }
    window.location.href = '/'
    throw new ApiError('Authentication required', 401)
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    const message = error?.error?.message || error?.detail || error?.message || 'API Error'
    throw new ApiError(message, response.status)
  }

  return response.json()
}

// ==================== SSE Streaming Types ====================

export interface SSEChunk {
  type: 'routing' | 'retrieval' | 'content' | 'thinking' | 'metadata' | 'done' | 'error'
  data: any
}

export interface RoutingData {
  router: string
  intent?: string
  confidence?: number
}

export interface RetrievalData {
  iteration: number
  strategy: string
  docs_retrieved: number
}

export interface ContentData {
  text: string
}

export interface MetadataData {
  citations?: any[]
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
    body: any
  ): AsyncGenerator<SSEChunk, void, unknown> {
    this.controller = new AbortController()

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
        signal: this.controller.signal,
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
        } catch (e) {
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
              const data = JSON.parse(match[1])
              yield data
            } catch (e) {
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
    conversationId?: string
  ): AsyncGenerator<SSEChunk, void, unknown> => {
    const client = new SSEClient()
    return client.stream('/api/v1/chat/stream', {
      message,
      conversation_id: conversationId,
    })
  },
}

/** Documents API */
export const documentsAPI = {
  list: async (): Promise<Document[]> => {
    const data = await fetchAPI<{ documents?: Document[]; items?: Document[] }>('/api/v1/documents/?page_size=100')
    return data.documents || data.items || []
  },

  upload: async (file: File): Promise<Document> => {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(`${API_BASE}/api/v1/documents/upload`, {
      method: 'POST',
      credentials: 'include',  // CRITICAL: Send httpOnly cookies
      body: formData,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      const message = error?.error?.message || error?.detail || error?.message || 'Upload failed'
      throw new ApiError(message, response.status)
    }

    return response.json()
  },

  delete: async (id: string): Promise<void> => {
    await fetchAPI<void>(`/api/v1/documents/${id}`, {
      method: 'DELETE',
    })
  },


  getDownloadUrl: (id: string): string => {
    // No token needed - httpOnly cookies are sent automatically
    return `${API_BASE}/api/v1/documents/${id}/download`
  },
}

/** Auth API (uses httpOnly cookies) */
export const authAPI = {
  login: async (email: string, password: string) => {
    const response = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
      credentials: 'include',  // CRITICAL: Receive httpOnly cookies
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      const message = error?.detail || 'Login failed'
      throw new ApiError(message, response.status)
    }

    return response.json()
  },

  register: async (email: string, password: string, full_name?: string) => {
    const response = await fetch(`${API_BASE}/api/v1/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, full_name }),
      credentials: 'include',  // CRITICAL: Receive httpOnly cookies
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      const message = error?.detail || 'Registration failed'
      throw new ApiError(message, response.status)
    }

    return response.json()
  },

  logout: async () => {
    const response = await fetch(`${API_BASE}/api/v1/auth/logout`, {
      method: 'POST',
      credentials: 'include',  // CRITICAL: Send cookies for logout
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      const message = error?.detail || 'Logout failed'
      throw new ApiError(message, response.status)
    }

    return response.json()
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
  sources?: any[]
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
  list: async (page = 1, pageSize = 20): Promise<ConversationListResponse> => {
    const data = await fetchAPI<any>(
      `/api/v1/chat/conversations?page=${page}&page_size=${pageSize}`
    )
    return {
      total: data.total,
      page: data.page || page,
      page_size: data.page_size || pageSize,
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
