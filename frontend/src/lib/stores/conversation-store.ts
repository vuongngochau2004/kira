import { create } from 'zustand'

interface ConversationStore {
  activeConversationId: string | null
  setActiveConversation: (id: string | null) => void
  clearActiveConversation: () => void
}

export const useConversationStore = create<ConversationStore>((set) => ({
  activeConversationId: null,

  setActiveConversation: (id: string | null) =>
    set({ activeConversationId: id }),

  clearActiveConversation: () =>
    set({ activeConversationId: null }),
}))
