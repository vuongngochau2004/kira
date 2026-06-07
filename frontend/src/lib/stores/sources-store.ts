import { create } from 'zustand'

export interface SourceItem {
  id: string
  type: 'pdf' | 'docx' | 'web'
  title: string
  snippet: string
  page?: number
  score: number
  document_id?: string
  content_length?: number  // For "view more" UI decision
  parent_document?: ParentDocumentInfo  // NEW: Link to parent document (grouped format)
}

export interface ParentDocumentInfo {
  document_id: string
  filename: string
  total_chunks: number
  relevance_score: number
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

    // Auto-detect response format (grouped vs flat)
    const isGrouped = rawSources.length > 0 &&
                         rawSources[0].hasOwnProperty('chunks')

    let mapped: SourceItem[]

    if (isGrouped) {
      // NEW STRUCTURE: Grouped by document
      // Flatten DocumentSource.chunks into SourceItem list
      mapped = rawSources.flatMap((docSource: any, docIdx: number) => {
        const docTitle = docSource.filename || docSource.title || 'Tài liệu'
        const docId = docSource.document_id || `doc-${docIdx}`

        return (docSource.chunks || []).map((chunk: any, chunkIdx: number) => {
          const title = docTitle
          let type: 'pdf' | 'docx' | 'web' = 'pdf'

          if (title.toLowerCase().endsWith('.docx') || title.toLowerCase().endsWith('.doc')) {
            type = 'docx'
          } else if (title.toLowerCase().startsWith('http') || docId === 'web') {
            type = 'web'
          }

          return {
            id: chunk.chunk_id || chunk.id || `${docId}-chunk-${chunkIdx}`,
            type,
            title, // Document title
            snippet: chunk.snippet || chunk.content || '',
            page: chunk.page,
            score: chunk.score,
            document_id: docId,
            content_length: chunk.content ? chunk.content.length : 0,
            // NEW: Link back to parent document
            parent_document: {
              document_id: docId,
              filename: docTitle,
              total_chunks: docSource.total_chunks_used,
              relevance_score: docSource.relevance_score
            }
          }
        })
      })
    } else {
      // LEGACY STRUCTURE: Flat list (backward compatible)
      mapped = rawSources.map((s, idx) => {
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
          snippet: s.snippet || s.content || '',
          page: s.page_number || (s.chunk_index !== undefined ? s.chunk_index + 1 : s.page),
          score: typeof s.score === 'number' ? s.score : 0.9,
          document_id: s.document_id || null,
          content_length: s.content_length,
          parent_document: undefined  // Legacy format doesn't have this
        }
      })
    }

    set({ sources: mapped })
  },

  setIsOpen: (isOpen) => set({ isOpen }),
  
  toggleOpen: () => set((state) => ({ isOpen: !state.isOpen })),

  setActiveSourceId: (activeSourceId) => set({ activeSourceId }),
}))
