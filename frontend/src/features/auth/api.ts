/** Auth API: login, register, logout and current user. */
import { API_BASE, ApiError } from '@/lib/api/http'

export interface AuthUser {
  id: string
  email: string
  full_name?: string
  role: string
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
