import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface AuthUser {
  id: string
  email: string
  full_name?: string
}

interface AuthState {
  user: AuthUser | null
  access_token: string | null
  isAuthenticated: boolean
  hasHydrated: boolean

  setHasHydrated: (state: boolean) => void
  setToken: (token: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      access_token: null,
      isAuthenticated: false,
      hasHydrated: false,

      setHasHydrated: (hasHydrated: boolean) => set({ hasHydrated }),

      setToken: (access_token: string) => {
        localStorage.setItem('access_token', access_token)
        set({
          access_token,
          isAuthenticated: true,
          user: { id: 'dev-user', email: 'dev@kira.local' }
        })
      },

      logout: () => {
        localStorage.removeItem('access_token')
        set({
          user: null,
          access_token: null,
          isAuthenticated: false,
        })
      },
    }),
    {
      name: 'kira-auth-storage',
      partialize: (state) => ({
        user: state.user,
        access_token: state.access_token,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true)
        // Sync token to localStorage
        if (state?.access_token) {
          localStorage.setItem('access_token', state.access_token)
        }
      },
    }
  )
)
