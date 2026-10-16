import { ApiError, apiErrorMessage, fetchAPI } from '@/lib/api/simple-client'
import type {
  CandidateReview,
  LegalDocument,
  LegalDocumentStatus,
  LegalUploadInput,
  ProvisionHistory,
  RelationCandidate,
  ReviewResult,
  TaskAccepted,
} from '@/lib/legal/types'

const BASE = '/api/v1/legal'

export const legalAPI = {
  listDocuments: (status?: LegalDocumentStatus) =>
    fetchAPI<LegalDocument[]>(`${BASE}/documents${status ? `?status=${status}` : ''}`),

  getDocument: (id: string) => fetchAPI<LegalDocument>(`${BASE}/documents/${id}`),

  listCandidates: (id: string) =>
    fetchAPI<RelationCandidate[]>(`${BASE}/documents/${id}/candidates`),

  /** Multipart upload; goes through fetch directly because fetchAPI forces a JSON content type. */
  upload: async (input: LegalUploadInput): Promise<LegalDocument> => {
    const form = new FormData()
    form.append('file', input.file)
    form.append('number', input.number)
    form.append('doc_type', input.doc_type)
    form.append('title', input.title)
    form.append('issuer', input.issuer)
    form.append('issued_date', input.issued_date)
    form.append('effective_date', input.effective_date)
    if (input.source_url) form.append('source_url', input.source_url)

    let response: Response
    try {
      response = await fetch(`${BASE}/documents`, {
        method: 'POST',
        credentials: 'include',
        body: form,
      })
    } catch {
      throw new ApiError('Network error', undefined)
    }
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new ApiError(apiErrorMessage(error, 'Tải lên thất bại'), response.status)
    }
    return response.json()
  },

  review: (candidateId: string, review: CandidateReview) =>
    fetchAPI<ReviewResult>(`${BASE}/candidates/${candidateId}`, {
      method: 'PATCH',
      body: JSON.stringify(review),
    }),

  publish: (id: string) =>
    fetchAPI<TaskAccepted>(`${BASE}/documents/${id}/publish`, { method: 'POST' }),

  reprocess: (id: string) =>
    fetchAPI<TaskAccepted>(`${BASE}/documents/${id}/reprocess`, { method: 'POST' }),

  remove: (id: string) => fetchAPI<void>(`${BASE}/documents/${id}`, { method: 'DELETE' }),

  provisionHistory: (key: string, date?: string) => {
    const params = new URLSearchParams({ key })
    if (date) params.set('date', date)
    return fetchAPI<ProvisionHistory>(`${BASE}/provisions?${params.toString()}`)
  },
}
