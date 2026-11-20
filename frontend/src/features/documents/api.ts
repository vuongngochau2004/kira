/** Documents API: upload, list, delete, chunks and downloads. */
import { API_BASE, ApiError, fetchAPI } from '@/lib/api/http'

export interface Document {
  id: string
  filename: string
  file_type: string
  file_size: number
  status: 'uploading' | 'processing' | 'completed' | 'failed' | string
  chunk_count?: number
  error_message?: string
  processing_task_id?: string
  created_at: string
  updated_at?: string
}

/** Documents API */
export const documentsAPI = {
  list: async (): Promise<Document[]> => {
    const data = await fetchAPI<{ documents?: Document[]; items?: Document[] }>('/api/v1/documents/?page_size=100')
    return data.documents || data.items || []
  },

  upload: async (file: File, signal?: AbortSignal): Promise<Document> => {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(`${API_BASE}/api/v1/documents/upload`, {
      method: 'POST',
      credentials: 'include',  // CRITICAL: Send httpOnly cookies
      body: formData,
      signal,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      const message = error?.error?.message || error?.detail || error?.message || 'Upload failed'
      throw new ApiError(message, response.status)
    }

    return response.json()
  },

  delete: async (id: string): Promise<void> => {
    await fetchAPI<void>(`/api/v1/documents/${id}`, {
      method: 'DELETE',
    })
  },

  cancel: async (id: string): Promise<{ document_id: string; success: boolean; message: string; status?: string }> => {
    return fetchAPI<{ document_id: string; success: boolean; message: string; status?: string }>(`/api/v1/documents/${id}/cancel`, {
      method: 'POST',
    })
  },


  getDownloadUrl: (id: string): string => {
    // No token needed - httpOnly cookies are sent automatically
    return `${API_BASE}/api/v1/documents/${id}/download`
  },

  getChunks: async (id: string): Promise<Array<{ id: string; chunk_index: number; content: string; metadata?: Record<string, unknown> }>> => {
    return fetchAPI<Array<{ id: string; chunk_index: number; content: string; metadata?: Record<string, unknown> }>>(`/api/v1/documents/${id}/chunks`)
  },
}
