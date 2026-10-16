'use client'

import { useCallback, useEffect, useState } from 'react'
import { legalAPI } from '@/lib/api/legal-client'
import { ACTIVE_DOCUMENT_STATUSES } from './format'
import type { LegalDocument } from './types'

export function useLegalDocuments(pollMs = 4000) {
  const [documents, setDocuments] = useState<LegalDocument[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    try {
      setDocuments(await legalAPI.listDocuments())
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không tải được danh sách văn bản')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  const hasActive = documents.some((document) => ACTIVE_DOCUMENT_STATUSES.includes(document.status))
  useEffect(() => {
    if (!hasActive) return
    const timer = setInterval(() => {
      void reload()
    }, pollMs)
    return () => clearInterval(timer)
  }, [hasActive, pollMs, reload])

  return { documents, isLoading, error, reload }
}
