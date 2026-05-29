'use client'

import { useState, useCallback, useEffect } from 'react'
import { documentsAPI, Document } from '@/lib/api/simple-client'
import { useAuthStore } from '@/lib/stores/auth-store'

export function useDocumentsUpload() {
  const { isAuthenticated } = useAuthStore()
  const [mounted, setMounted] = useState(false)
  const [documents, setDocuments] = useState<Document[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [uploadingFiles, setUploadingFiles] = useState<Set<string>>(new Set())

  useEffect(() => {
    setMounted(true)
  }, [])

  const loadDocuments = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const docs = await documentsAPI.list()
      setDocuments(docs)
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

  const uploadDocument = useCallback(async (file: File): Promise<Document> => {
    setError(null)

    // Add to uploading set
    setUploadingFiles((prev) => new Set(prev).add(file.name))

    try {
      const doc = await documentsAPI.upload(file)

      // Add to documents list
      setDocuments((prev) => [doc, ...prev])

      return doc
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : `Không thể tải lên ${file.name}`
      setError(errorMessage)
      throw err
    } finally {
      // Remove from uploading set
      setUploadingFiles((prev) => {
        const newSet = new Set(prev)
        newSet.delete(file.name)
        return newSet
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
  }
}
