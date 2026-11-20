/** Shared HTTP helpers: API base URL, fetch wrapper with cookie auth, API errors. */
import { getBackendUrl } from '@/lib/api/backend-url'

const getApiBase = () => {
  if (typeof window !== 'undefined') {
    // Client-side: use Next.js proxy rewrites to avoid CORS/network issues
    return ''
  }
  // Server-side default
  return getBackendUrl()
}

export const API_BASE = getApiBase()

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/** Human-readable message from a FastAPI/KIRA error body (a 422 `detail` is a list). */
export function apiErrorMessage(error: unknown, fallback: string): string {
  const body = (error ?? {}) as {
    error?: { message?: string }
    detail?: unknown
    message?: unknown
  }
  if (body.error?.message) return body.error.message
  if (typeof body.detail === 'string') return body.detail
  if (Array.isArray(body.detail)) {
    const parts = body.detail
      .map((item) =>
        item && typeof item === 'object' && 'msg' in item ? String((item as { msg: unknown }).msg) : '',
      )
      .filter(Boolean)
    if (parts.length > 0) return parts.join('; ')
  }
  if (typeof body.message === 'string') return body.message
  return fallback
}

/** Simple fetch wrapper with auth (uses httpOnly cookies) */
export async function fetchAPI<T>(
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
  } catch {
    throw new ApiError('Network error', undefined)
  }

  if (response.status === 401) {
    // Token expired or invalid - clear auth state and redirect to login
    // Import dynamically to avoid circular dependency
    if (typeof window !== 'undefined') {
      import('@/features/auth/store').then(({ useAuthStore }) => {
        useAuthStore.getState().clearAuth()
      })
    }
    window.location.href = '/'
    throw new ApiError('Authentication required', 401)
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new ApiError(apiErrorMessage(error, 'API Error'), response.status)
  }

  if (response.status === 204) {
    return undefined as T
  }
  const body = await response.text()
  return (body ? JSON.parse(body) : undefined) as T
}

// ==================== SSE Streaming Types ====================
