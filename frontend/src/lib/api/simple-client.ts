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
  status: 'pending' | 'processing' | 'completed' | 'failed'
  created_at: string
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

/** Simple fetch wrapper with auth */
async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null

  console.log(`[DEBUG fetchAPI] Sending request to ${API_BASE}${endpoint}`, { method: options?.method || 'GET', options });

  let response;
  try {
    response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        ...options?.headers,
      },
    })
    console.log(`[DEBUG fetchAPI] Received response from ${API_BASE}${endpoint}:`, response.status, response.statusText);
  } catch (error) {
    console.error(`[DEBUG fetchAPI] Network error when fetching ${API_BASE}${endpoint}:`, error);
    throw error;
  }

  if (response.status === 401) {
    // Try refresh token
    try {
      const { useAuthStore } = await import('../stores/auth-store')
      const store = useAuthStore.getState()
      await store.refreshTokens()
      // Retry with new token
      const newToken = localStorage.getItem('access_token')
      const retryResponse = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(newToken ? { 'Authorization': `Bearer ${newToken}` } : {}),
          ...options?.headers,
        },
      })
      if (!retryResponse.ok) {
        const error = await retryResponse.json().catch(() => ({}))
        const message = error?.error?.message || error?.detail || error?.message || 'API Error'
        throw new ApiError(message, retryResponse.status)
      }
      return retryResponse.json()
    } catch {
      // Refresh failed, redirect to login
      const { useAuthStore } = await import('../stores/auth-store')
      await useAuthStore.getState().logout()
      window.location.href = '/'
      throw new ApiError('Authentication required', 401)
    }
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    const message = error?.error?.message || error?.detail || error?.message || 'API Error'
    throw new ApiError(message, response.status)
  }

  return response.json()
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
}

/** Documents API */
export const documentsAPI = {
  list: async (): Promise<Document[]> => {
    const data = await fetchAPI<{ items: Document[] }>('/api/v1/documents/?page_size=100')
    return data.items
  },

  upload: async (file: File): Promise<Document> => {
    const formData = new FormData()
    formData.append('file', file)
    const token = localStorage.getItem('access_token')

    const response = await fetch(`${API_BASE}/api/v1/documents/upload`, {
      method: 'POST',
      headers: {
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
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
}

/** Auth API */
export const authAPI = {
  login: async (email: string, password: string) => {
    const response = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
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
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      const message = error?.detail || 'Registration failed'
      throw new ApiError(message, response.status)
    }

    return response.json()
  },

  refresh: async (refresh_token: string) => {
    const response = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token }),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      const message = error?.detail || 'Refresh failed'
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
  list: (page = 1, pageSize = 20) =>
    fetchAPI<ConversationListResponse>(
      `/api/v1/chat/conversations?page=${page}&page_size=${pageSize}`
    ),

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
