/**
 * Source Panel State Management
 * Centralized state management using useReducer pattern
 */

import type {
  SourcePanelUIState,
  SourcePanelAction,
  DocumentData,
} from '../types/source-panel-types'

// ============================================
// Initial State
// ============================================

export const createInitialSourcePanelState = (): SourcePanelUIState => ({
  expandedDocument: null,
  selectedChunk: null,
  clipboard: {
    id: null,
    timestamp: 0,
  },
})

// ============================================
// Reducer
// ============================================

export const sourcePanelReducer = (
  state: SourcePanelUIState,
  action: SourcePanelAction
): SourcePanelUIState => {
  switch (action.type) {
    case 'EXPAND_DOCUMENT':
      return {
        ...state,
        expandedDocument: action.payload,
        // Reset selected chunk when document changes
        selectedChunk: null,
      }

    case 'SELECT_CHUNK':
      return {
        ...state,
        selectedChunk: action.payload,
      }

    case 'COPY_TO_CLIPBOARD':
      return {
        ...state,
        clipboard: {
          id: action.payload.id,
          timestamp: action.payload.timestamp,
        },
      }

    default:
      return state
  }
}

// ============================================
// Document Data State Management
// ============================================

interface DocumentDataState {
  documents: Record<string, DocumentData>
}

type DocumentDataAction =
  | { type: 'LOAD_START'; payload: string }
  | { type: 'LOAD_SUCCESS'; payload: { id: string; data: DocumentData['chunks'] } }
  | { type: 'LOAD_ERROR'; payload: { id: string; error: string } }

export const createInitialDocumentDataState = (): DocumentDataState => ({
  documents: {},
})

export const documentDataReducer = (
  state: DocumentDataState,
  action: DocumentDataAction
): DocumentDataState => {
  switch (action.type) {
    case 'LOAD_START':
      return {
        ...state,
        documents: {
          ...state.documents,
          [action.payload]: {
            document_id: action.payload,
            chunks: [],
            loading: true,
            error: null,
          },
        },
      }

    case 'LOAD_SUCCESS':
      return {
        ...state,
        documents: {
          ...state.documents,
          [action.payload.id]: {
            document_id: action.payload.id,
            chunks: action.payload.data,
            loading: false,
            error: null,
          },
        },
      }

    case 'LOAD_ERROR':
      return {
        ...state,
        documents: {
          ...state.documents,
          [action.payload.id]: {
            document_id: action.payload.id,
            chunks: [],
            loading: false,
            error: action.payload.error,
          },
        },
      }

    default:
      return state
  }
}
