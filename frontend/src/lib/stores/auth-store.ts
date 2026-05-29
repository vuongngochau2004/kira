import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const getApiBase = () => {
  if (typeof window !== 'undefined') {
    return '/api/v1'
  }
  return 'http://127.0.0.1:8888/api/v1'
}


export interface AuthUser {
  id: string
  email: string
  full_name?: string
  role: string
}

interface AuthState {
  user: AuthUser | null
  access_token: string | null
  refresh_token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, full_name?: string) => Promise<void>
  logout: () => Promise<void>
  refreshTokens: () => Promise<void>
  clearError: () => void
  setTokens: (access: string, refresh: string) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      access_token: null,
      refresh_token: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      setTokens: (access: string, refresh: string) => {
        localStorage.setItem('access_token', access)
        set({ access_token: access, refresh_token: refresh })
      },

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await fetch(`${getApiBase()}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
          })

          if (!response.ok) {
            const error = await response.json()
            throw new Error(error.detail || 'Login failed')
          }

          const data = await response.json()
          set({
            user: {
              id: data.id,
              email: data.email,
              full_name: data.full_name,
              role: data.role,
            },
            access_token: data.access_token || data.tokens?.access_token,
            refresh_token: data.refresh_token || data.tokens?.refresh_token,
            isAuthenticated: true,
            isLoading: false,
          })
          localStorage.setItem('access_token', data.access_token || data.tokens?.access_token)
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Login failed',
            isLoading: false,
          })
          throw error
        }
      },

      register: async (email: string, password: string, full_name?: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await fetch(`${getApiBase()}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, full_name }),
          })

          if (!response.ok) {
            const error = await response.json()
            throw new Error(error.detail || 'Registration failed')
          }

          const data = await response.json()
          set({
            user: {
              id: data.id,
              email: data.email,
              full_name: data.full_name,
              role: data.role,
            },
            access_token: data.access_token || data.tokens?.access_token,
            refresh_token: data.refresh_token || data.tokens?.refresh_token,
            isAuthenticated: true,
            isLoading: false,
          })
          localStorage.setItem('access_token', data.access_token || data.tokens?.access_token)
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Registration failed',
            isLoading: false,
          })
          throw error
        }
      },

      refreshTokens: async () => {
        const { refresh_token } = get()
        if (!refresh_token) throw new Error('No refresh token')

        try {
          const response = await fetch(`${getApiBase()}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token }),
          })

          if (!response.ok) throw new Error('Refresh failed')

          const data = await response.json()
          set({
            access_token: data.access_token,
          })
          localStorage.setItem('access_token', data.access_token)
        } catch (error) {
          // Clear auth on refresh failure
          set({
            user: null,
            access_token: null,
            refresh_token: null,
            isAuthenticated: false,
          })
          localStorage.removeItem('access_token')
          throw error
        }
      },

      logout: async () => {
        set({
          user: null,
          access_token: null,
          refresh_token: null,
          isAuthenticated: false,
        })
        localStorage.removeItem('access_token')
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'kira-auth-storage',
      partialize: (state) => ({
        user: state.user,
        access_token: state.access_token,
        refresh_token: state.refresh_token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
