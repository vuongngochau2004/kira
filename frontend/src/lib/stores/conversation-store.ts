import { create } from 'zustand'

interface ConversationStore {
  // State
  activeConversationId: string | null
  isLoading: boolean
  error: string | null

  // Actions
  setActiveConversation: (id: string | null) => void
  clearActiveConversation: () => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void

  // URL synchronization
  updateURL: (id: string) => void
  syncFromURL: (id: string | null) => boolean
}

export const useConversationStore = create<ConversationStore>((set, get) => ({
  // Initial state
  activeConversationId: null,
  isLoading: false,
  error: null,

  // Basic actions
  setActiveConversation: (id: string | null) =>
    set({ activeConversationId: id, error: null }),

  clearActiveConversation: () =>
    set({ activeConversationId: null, error: null }),

  setLoading: (loading: boolean) =>
    set({ isLoading: loading }),

  setError: (error: string | null) =>
    set({ error }),

  // URL synchronization
  updateURL: (id: string) => {
    if (typeof window === 'undefined') return

    const url = new URL(window.location.href)
    url.searchParams.set('id', id)

    // Use replace to avoid polluting browser history
    window.history.replaceState({}, '', url.toString())
  },

  syncFromURL: (id: string | null) => {
    if (!id) {
      set({ activeConversationId: null })
      return false
    }

    // Basic UUID validation (same as utility)
    const isValid = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(id)

    if (isValid) {
      set({ activeConversationId: id, error: null })
      return true
    }

    set({ activeConversationId: null, error: 'Invalid conversation ID' })
    return false
  },
}))
