import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const getApiBase = () => {
  return '/api/v1'
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
  isVerified: boolean // Track if authentication has been verified with backend

  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, full_name?: string) => Promise<void>
  logout: () => Promise<void>
  refreshTokens: () => Promise<void>
  clearError: () => void
  setTokens: (access: string, refresh: string) => void
  setHydrated: () => void
  setIsVerified: (verified: boolean) => void
  verifyAuth: () => Promise<void> // Verify auth state with backend
  clearAuth: () => void // Clear auth state (called on 401)
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
      isVerified: false, // Auth verification not done yet

      setTokens: (access: string, refresh: string) => {
        // Tokens are now stored in httpOnly cookies, no localStorage needed
        set({ access_token: access, refresh_token: refresh })
      },

      setIsVerified: (verified: boolean) => {
        set({ isVerified: verified })
      },

      verifyAuth: async () => {
        // Verify authentication state with backend
        // This prevents localStorage/cookies mismatch
        try {
          const response = await fetch(`${getApiBase()}/auth/me`, {
            method: 'GET',
            credentials: 'include',  // Send httpOnly cookies
            headers: { 'Content-Type': 'application/json' },
          })

          if (!response.ok) {
            // Not authenticated - clear state
            set({
              user: null,
              isAuthenticated: false,
              isVerified: true,
            })
            return
          }

          const data = await response.json()
          set({
            user: {
              id: data.id,
              email: data.email,
              full_name: data.full_name,
              role: data.role,
            },
            isAuthenticated: true,
            isVerified: true,
          })
        } catch (error) {
          // Network error or auth failed - clear state
          set({
            user: null,
            isAuthenticated: false,
            isVerified: true,
          })
        }
      },

      clearAuth: () => {
        // Clear all auth state - called on 401 errors
        set({
          user: null,
          access_token: null,
          refresh_token: null,
          isAuthenticated: false,
          isVerified: true, // Verified as not authenticated
          error: 'Session expired. Please login again.',
        })
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
            isVerified: true, // Auth verified after successful login
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
            isVerified: true, // Auth verified after successful registration
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
            isVerified: true, // Verified after successful refresh
          })
        } catch (error) {
          // Clear auth on refresh failure
          set({
            user: null,
            access_token: null,
            refresh_token: null,
            isAuthenticated: false,
            isVerified: true, // Verified as not authenticated
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
          // Ignore logout errors
        } finally {
          // Always clear local state
          set({
            user: null,
            access_token: null,
            refresh_token: null,
            isAuthenticated: false,
            isVerified: true, // Verified as not authenticated
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
        // After hydration, verify auth state with backend
        // This runs async and doesn't block hydration
        if (typeof window !== 'undefined' && state?.isAuthenticated) {
          // If localStorage says authenticated, verify with backend
          state?.verifyAuth()
        } else {
          // If not authenticated in localStorage, mark as verified immediately
          state?.setIsVerified(true)
        }
      },
    }
  )
)
