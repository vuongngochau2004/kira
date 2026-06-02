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
  isHydrated: boolean // Track if persist middleware has hydrated

  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, full_name?: string) => Promise<void>
  logout: () => Promise<void>
  refreshTokens: () => Promise<void>
  clearError: () => void
  setTokens: (access: string, refresh: string) => void
  setHydrated: () => void
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
      isHydrated: false,

      setTokens: (access: string, refresh: string) => {
        // Tokens are now stored in httpOnly cookies, no localStorage needed
        set({ access_token: access, refresh_token: refresh })
      },

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await fetch(`${getApiBase()}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',  // Send/receive httpOnly cookies
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
            access_token: null,  // Tokens now in httpOnly cookies
            refresh_token: null,
            isAuthenticated: true,
            isLoading: false,
          })
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
            credentials: 'include',  // Send/receive httpOnly cookies
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
            access_token: null,  // Tokens now in httpOnly cookies
            refresh_token: null,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Registration failed',
            isLoading: false,
          })
          throw error
        }
      },

      refreshTokens: async () => {
        // Note: With httpOnly cookies, the backend automatically handles refresh
        // This is kept for backward compatibility but may not be needed
        try {
          const response = await fetch(`${getApiBase()}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',  // Send/receive httpOnly cookies
            body: JSON.stringify({ refresh_token: 'cookie' }),  // Placeholder, backend reads from cookie
          })

          if (!response.ok) throw new Error('Refresh failed')

          const data = await response.json()
          set({
            user: {
              id: data.id,
              email: data.email,
              full_name: data.full_name,
              role: data.role,
            },
          })
        } catch (error) {
          // Clear auth on refresh failure
          set({
            user: null,
            access_token: null,
            refresh_token: null,
            isAuthenticated: false,
          })
          throw error
        }
      },

      logout: async () => {
        try {
          // Call backend to clear cookies
          await fetch(`${getApiBase()}/auth/logout`, {
            method: 'POST',
            credentials: 'include',  // Send/receive httpOnly cookies
          })
        } catch (error) {
          console.error('Logout error:', error)
        } finally {
          // Always clear local state
          set({
            user: null,
            access_token: null,
            refresh_token: null,
            isAuthenticated: false,
          })
          // Clean up returnUrl to prevent stale redirects after logout
          sessionStorage.removeItem('returnUrl')
        }
      },

      clearError: () => set({ error: null }),
      setHydrated: () => set({ isHydrated: true }),
    }),
    {
      name: 'kira-auth-storage',
      partialize: (state) => ({
        user: state.user,
        // Don't persist tokens - they're in httpOnly cookies now
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHydrated()
      },
    }
  )
)
