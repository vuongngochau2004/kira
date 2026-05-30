'use client'

import { useState, useCallback, useEffect } from 'react'
import { documentsAPI, Document } from '@/lib/api/simple-client'
import { useAuthStore } from '@/lib/stores/auth-store'

const parseUtcDate = (dateStr?: string) => {
  if (!dateStr) return null
  const normalized = dateStr.endsWith('Z') ? dateStr : `${dateStr}Z`
  const parsed = Date.parse(normalized)
  return isNaN(parsed) ? null : new Date(parsed)
}

export function useDocumentsUpload() {
  const { isAuthenticated } = useAuthStore()
  const [mounted, setMounted] = useState(false)
  const [documents, setDocuments] = useState<Document[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [uploadingFiles, setUploadingFiles] = useState<Set<string>>(new Set())
  const [uploadDurations, setUploadDurations] = useState<Record<string, number>>({})
  const [documentStarts, setDocumentStarts] = useState<Record<string, number>>({})
  const [activeUploadStarts, setActiveUploadStarts] = useState<Record<string, number>>({})

  // Load state from localStorage on mount
  useEffect(() => {
    setMounted(true)
    if (typeof window !== 'undefined') {
      try {
        const savedDurations = localStorage.getItem('kira-upload-durations')
        if (savedDurations) {
          setUploadDurations(JSON.parse(savedDurations))
        }
        const savedStarts = localStorage.getItem('kira-document-starts')
        if (savedStarts) {
          setDocumentStarts(JSON.parse(savedStarts))
        }
      } catch (e) {
        console.error('Failed to load timing states:', e)
      }
    }
  }, [])

  const loadDocuments = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const docs = await documentsAPI.list()
      setDocuments(docs || [])
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Không thể tải danh sách tài liệu'
      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Load documents when authenticated and mounted
  useEffect(() => {
    if (mounted && isAuthenticated) {
      loadDocuments()
    } else {
      setDocuments([])
    }
  }, [mounted, isAuthenticated, loadDocuments])

  // Automatically poll document list when there are files in 'uploading' or 'processing' status
  useEffect(() => {
    if (!mounted || !isAuthenticated) return

    const hasActiveTasks = documents.some(
      (doc) => doc.status === 'uploading' || doc.status === 'processing'
    )
    if (!hasActiveTasks && uploadingFiles.size === 0) return

    const interval = setInterval(() => {
      loadDocuments()
    }, 4000)

    return () => clearInterval(interval)
  }, [mounted, isAuthenticated, documents, uploadingFiles, loadDocuments])

  // Automatically detect completed/failed transitions to compute and save final durations
  useEffect(() => {
    if (!mounted) return

    let updated = false
    const nextDurations = { ...uploadDurations }

    documents.forEach((doc) => {
      if (doc.status === 'completed' || doc.status === 'failed') {
        if (nextDurations[doc.id] === undefined) {
          const startTime = documentStarts[doc.id]
          if (startTime) {
            // End-to-end duration = server completion time - client upload start time
            const serverEndTime = doc.updated_at ? parseUtcDate(doc.updated_at)?.getTime() : null
            if (serverEndTime) {
              const duration = Math.max(0.1, (serverEndTime - startTime) / 1000)
              nextDurations[doc.id] = duration
              updated = true
            } else {
              // Fallback to polling completion time if updated_at is missing
              const duration = Math.max(0.1, (Date.now() - startTime) / 1000)
              nextDurations[doc.id] = duration
              updated = true
            }
          } else if (doc.created_at && doc.updated_at) {
            // Fallback for page refresh / missing start time: server processing duration
            const serverStartTime = parseUtcDate(doc.created_at)?.getTime()
            const serverEndTime = parseUtcDate(doc.updated_at)?.getTime()
            if (serverStartTime && serverEndTime) {
              const duration = Math.max(0.1, (serverEndTime - serverStartTime) / 1000)
              nextDurations[doc.id] = duration
              updated = true
            }
          }
        }
      }
    })

    if (updated) {
      setUploadDurations(nextDurations)
      if (typeof window !== 'undefined') {
        try {
          localStorage.setItem('kira-upload-durations', JSON.stringify(nextDurations))
        } catch (e) {
          console.error('Failed to save upload durations:', e)
        }
      }
    }
  }, [mounted, documents, documentStarts, uploadDurations])

  const uploadDocument = useCallback(async (file: File): Promise<Document> => {
    setError(null)

    // Add to uploading set & record active upload start time
    setUploadingFiles((prev) => new Set(prev).add(file.name))
    const startTime = Date.now()
    setActiveUploadStarts((prev) => ({ ...prev, [file.name]: startTime }))

    try {
      const doc = await documentsAPI.upload(file)

      // Record start time mapped by document ID in state & localStorage
      setDocumentStarts((prev) => {
        const next = { ...prev, [doc.id]: startTime }
        if (typeof window !== 'undefined') {
          try {
            localStorage.setItem('kira-document-starts', JSON.stringify(next))
          } catch (e) {
            console.error('Failed to save document starts:', e)
          }
        }
        return next
      })

      // Add to documents list
      setDocuments((prev) => [doc, ...prev])

      return doc
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : `Không thể tải lên ${file.name}`
      setError(errorMessage)
      throw err
    } finally {
      // Remove from uploading set & active starts
      setUploadingFiles((prev) => {
        const newSet = new Set(prev)
        newSet.delete(file.name)
        return newSet
      })
      setActiveUploadStarts((prev) => {
        const next = { ...prev }
        delete next[file.name]
        return next
      })
    }
  }, [])

  const deleteDocument = useCallback(async (id: string) => {
    setError(null)

    try {
      await documentsAPI.delete(id)

      // Remove from documents list
      setDocuments((prev) => prev.filter((d) => d.id !== id))
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Không thể xoá tài liệu'
      setError(errorMessage)
      throw err
    }
  }, [])

  const isUploading = useCallback((filename: string) => {
    return uploadingFiles.has(filename)
  }, [uploadingFiles])

  return {
    documents,
    isLoading,
    error,
    uploadDocument,
    deleteDocument,
    loadDocuments,
    isUploading,
    refetch: loadDocuments,
    uploadDurations,
    documentStarts,
    activeUploadStarts,
  }
}
