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
  conversationId: string | null
  isOpen: boolean
  activeSourceId: string | null
  setSources: (rawSources: any[]) => void
  replaceForConversation: (conversationId: string | null, rawSources: any[]) => void
  setIsOpen: (isOpen: boolean) => void
  toggleOpen: () => void
  setActiveSourceId: (id: string | null) => void
  reset: () => void
}

function getSourceType(title: string, documentId?: string | null): 'pdf' | 'docx' | 'web' {
  const normalizedTitle = title.toLowerCase()

  if (normalizedTitle.endsWith('.docx') || normalizedTitle.endsWith('.doc')) {
    return 'docx'
  }

  if (normalizedTitle.startsWith('http') || documentId === 'web') {
    return 'web'
  }

  return 'pdf'
}

function mapSources(rawSources: any[] | null | undefined): SourceItem[] {
  if (!rawSources || rawSources.length === 0) {
    return []
  }

  // Auto-detect response format (grouped vs flat)
  const isGrouped = rawSources[0]?.hasOwnProperty('chunks')

  if (isGrouped) {
    // Grouped by document: flatten DocumentSource.chunks into SourceItem list.
    return rawSources.flatMap((docSource: any, docIdx: number) => {
      const docTitle = docSource.filename || docSource.title || 'Tài liệu'
      const docId = docSource.document_id || `doc-${docIdx}`
      const type = getSourceType(docTitle, docId)

      return (docSource.chunks || []).map((chunk: any, chunkIdx: number) => ({
        id: chunk.chunk_id || chunk.id || `${docId}-chunk-${chunkIdx}`,
        type,
        title: docTitle,
        snippet: chunk.snippet || chunk.content || '',
        page: chunk.page_number || chunk.page,
        score: typeof chunk.score === 'number' ? chunk.score : 0.9,
        document_id: docId,
        content_length: chunk.content_length || (chunk.content ? chunk.content.length : 0),
        parent_document: {
          document_id: docId,
          filename: docTitle,
          total_chunks: docSource.total_chunks_used,
          relevance_score: docSource.relevance_score,
        },
      }))
    })
  }

  return rawSources.map((source, idx) => {
    const title = source.title || source.source || 'Tài liệu'
    const documentId = source.document_id || null

    return {
      id: source.chunk_id || source.id || `${documentId || title}-source-${idx}`,
      type: getSourceType(title, documentId),
      title,
      snippet: source.snippet || source.content || '',
      page: source.page_number || (source.chunk_index !== undefined ? source.chunk_index + 1 : source.page),
      score: typeof source.score === 'number'
        ? source.score
        : typeof source.grounding_score === 'number'
          ? source.grounding_score
          : 0.9,
      document_id: documentId,
      content_length: source.content_length || (source.content ? source.content.length : undefined),
      parent_document: undefined,
    }
  })
}

export const useSourcesStore = create<SourcesState>((set) => ({
  sources: [],
  conversationId: null,
  isOpen: false,
  activeSourceId: null,

  setSources: (rawSources) =>
    set((state) => {
      const sources = mapSources(rawSources)
      const activeSourceId = state.activeSourceId && sources.some((source) => source.id === state.activeSourceId)
        ? state.activeSourceId
        : null

      return { sources, activeSourceId }
    }),

  replaceForConversation: (conversationId, rawSources) =>
    set((state) => {
      const sources = mapSources(rawSources)
      const isSameConversation = state.conversationId === conversationId
      const activeSourceId = isSameConversation &&
        state.activeSourceId &&
        sources.some((source) => source.id === state.activeSourceId)
          ? state.activeSourceId
          : null

      return {
        conversationId,
        sources,
        activeSourceId,
      }
    }),

  setIsOpen: (isOpen) => set({ isOpen }),
  
  toggleOpen: () => set((state) => ({ isOpen: !state.isOpen })),

  setActiveSourceId: (activeSourceId) => set({ activeSourceId }),

  reset: () => set({ sources: [], conversationId: null, isOpen: false, activeSourceId: null }),
}))
