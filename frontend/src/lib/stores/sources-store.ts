import { create } from 'zustand'

export interface SourceItem {
  id: string
  type: 'pdf' | 'docx' | 'web'
  title: string
  snippet: string
  page?: number
  score: number
  document_id?: string
}

interface SourcesState {
  sources: SourceItem[]
  isOpen: boolean
  activeSourceId: string | null
  setSources: (rawSources: any[]) => void
  setIsOpen: (isOpen: boolean) => void
  toggleOpen: () => void
  setActiveSourceId: (id: string | null) => void
}

export const useSourcesStore = create<SourcesState>((set) => ({
  sources: [],
  isOpen: false,
  activeSourceId: null,

  setSources: (rawSources) => {
    if (!rawSources) {
      set({ sources: [] })
      return
    }

    const mapped = rawSources.map((s, idx) => {
      const title = s.title || s.source || 'Tài liệu'
      let type: 'pdf' | 'docx' | 'web' = 'pdf'
      
      if (title.toLowerCase().endsWith('.docx') || title.toLowerCase().endsWith('.doc')) {
        type = 'docx'
      } else if (title.toLowerCase().startsWith('http') || s.document_id === 'web') {
        type = 'web'
      }

      return {
        id: s.chunk_id || s.id || `source-${idx}-${Date.now()}`,
        type,
        title,
        snippet: s.content || s.snippet || '',
        page: s.chunk_index !== undefined ? s.chunk_index + 1 : s.page,
        score: typeof s.score === 'number' ? s.score : 0.9,
        document_id: s.document_id || null,
      }
    })

    set({ sources: mapped })
  },

  setIsOpen: (isOpen) => set({ isOpen }),
  
  toggleOpen: () => set((state) => ({ isOpen: !state.isOpen })),

  setActiveSourceId: (activeSourceId) => set({ activeSourceId }),
}))
