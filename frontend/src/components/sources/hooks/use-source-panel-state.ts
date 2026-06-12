/**
 * Source Panel State Hook
 * Custom hook for managing source panel state with reducer
 */

import { useReducer, useCallback, useEffect } from 'react'
import { useSourcesStore } from '@/lib/stores/sources-store'
import {
  sourcePanelReducer,
  createInitialSourcePanelState,
} from '../state/source-panel-reducer'

export function useSourcePanelState() {
  const store = useSourcesStore()
  const [state, dispatch] = useReducer(
    sourcePanelReducer,
    null,
    createInitialSourcePanelState
  )

  // ============================================
  // Document Actions
  // ============================================

  const expandDocument = useCallback((documentId: string | null) => {
    dispatch({
      type: 'EXPAND_DOCUMENT',
      payload: documentId,
    })
  }, [])

  const selectChunk = useCallback((chunkId: string | null) => {
    dispatch({
      type: 'SELECT_CHUNK',
      payload: chunkId,
    })
  }, [])

  const copyToClipboard = useCallback(
    async (id: string, text: string): Promise<boolean> => {
      try {
        await navigator.clipboard.writeText(text)
        dispatch({
          type: 'COPY_TO_CLIPBOARD',
          payload: { id, timestamp: Date.now() },
        })
        return true
      } catch (err) {
        console.error('Failed to copy to clipboard:', err)
        return false
      }
    },
    []
  )

  // ============================================
  // Store Synchronization
  // ============================================

  // Sync with store's active source
  useEffect(() => {
    if (store.activeSourceId && store.activeSourceId !== state.selectedChunk) {
      const matchedSource = store.sources.find((s) => s.id === store.activeSourceId)
      if (matchedSource) {
        const docKey = matchedSource.document_id || matchedSource.title
        expandDocument(docKey)
        selectChunk(store.activeSourceId)
      }
    }
  }, [store.activeSourceId, store.sources, expandDocument, selectChunk, state.selectedChunk])

  return {
    state,
    store,
    expandDocument,
    selectChunk,
    copyToClipboard,
  }
}
