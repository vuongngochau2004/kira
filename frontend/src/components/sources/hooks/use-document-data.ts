/**
 * Document Data Hook
 * Custom hook for loading and managing document chunks
 */

import { useState, useCallback, useEffect } from 'react'
import { documentsAPI } from '@/lib/api/simple-client'
import type { DocumentData, DocumentChunk } from '../types/source-panel-types'

export function useDocumentData(expandedDocumentId: string | null) {
  const [documents, setDocuments] = useState<Record<string, DocumentData>>({})
  const [loading, setLoading] = useState<Record<string, boolean>>({})

  // Load document chunks when expanded
  useEffect(() => {
    if (expandedDocumentId && documents[expandedDocumentId] === undefined && !loading[expandedDocumentId]) {
      setLoading((prev) => ({ ...prev, [expandedDocumentId]: true }))

      documentsAPI
        .getChunks(expandedDocumentId)
        .then((chunks) => {
          setDocuments((prev) => ({
            ...prev,
            [expandedDocumentId]: {
              document_id: expandedDocumentId,
              chunks,
              loading: false,
              error: null,
            },
          }))
        })
        .catch((err) => {
          console.error('Failed to load document chunks:', err)
          setDocuments((prev) => ({
            ...prev,
            [expandedDocumentId]: {
              document_id: expandedDocumentId,
              chunks: [],
              loading: false,
              error: err.message || 'Failed to load document',
            },
          }))
        })
        .finally(() => {
          setLoading((prev) => ({ ...prev, [expandedDocumentId]: false }))
        })
    }
  }, [expandedDocumentId, documents, loading])

  const getDocumentData = useCallback(
    (documentId: string): DocumentData | null => {
      return documents[documentId] || null
    },
    [documents]
  )

  const isLoadingDocument = useCallback(
    (documentId: string): boolean => {
      return loading[documentId] || false
    },
    [loading]
  )

  return {
    documents,
    getDocumentData,
    isLoadingDocument,
  }
}
