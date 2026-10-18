import { fireEvent, render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { legalAPI } from '@/lib/api/legal-client'
import type { LegalDocument, RelationCandidate } from '@/lib/legal/types'
import { useAuthStore } from '@/lib/stores/auth-store'
import LegalDocumentPage from './page'

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: 'd1' }),
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('@/components/auth/auth-guard', () => ({
  AuthGuard: ({ children }: { children: ReactNode }) => children,
}))
vi.mock('@/lib/api/legal-client', () => ({
  legalAPI: {
    getDocument: vi.fn(),
    listCandidates: vi.fn(),
    review: vi.fn(),
    publish: vi.fn(),
    reprocess: vi.fn(),
    remove: vi.fn(),
  },
}))

const DOCUMENT = {
  id: 'd1',
  number: '99/2026/QH15',
  doc_type: 'law',
  title: 'Luật sửa đổi',
  issuer: 'Quốc hội',
  issued_date: '2026-06-01',
  effective_date: '2026-07-01',
  source_url: null,
  status: 'published',
  warnings: [],
  error_detail: null,
  provision_count: 3,
  published_at: '2026-07-01T00:00:00',
  created_at: null,
} as LegalDocument

const CANDIDATE = {
  id: 'c1',
  legal_document_id: 'd1',
  type: 'AMENDS',
  source_provision_key: '99/2026/QH15#D1.K1',
  target_number: '31/2024/QH15',
  target_provision_ref: 'D3.K1',
  effective_date: '2026-07-01',
  new_text: '1. Mới.',
  evidence_text: 'Sửa đổi khoản 1 Điều 3',
  evidence_page: null,
  extractor: 'rule',
  confidence: 0.7,
  status: 'pending',
  flags: [],
  reviewed_by: null,
  reviewed_at: null,
  review_note: null,
} as RelationCandidate

beforeEach(() => {
  useAuthStore.setState({ user: { id: 'u1', email: 'a@b.c', role: 'admin' } })
  vi.mocked(legalAPI.getDocument).mockResolvedValue(DOCUMENT)
  vi.mocked(legalAPI.listCandidates).mockResolvedValue([CANDIDATE])
})

describe('legal document page', () => {
  it('tells the admin when an approval republishes the document', async () => {
    vi.mocked(legalAPI.review).mockResolvedValue({
      candidate: { ...CANDIDATE, status: 'approved' },
      republish_task_id: 't1',
    })
    render(<LegalDocumentPage />)
    fireEvent.click(await screen.findByRole('button', { name: 'Duyệt' }))
    expect(
      await screen.findByText('Đã lưu. Văn bản đang được xuất bản lại để cập nhật đồ thị.'),
    ).toBeInTheDocument()
  })

  it('confirms a plain review decision', async () => {
    vi.mocked(legalAPI.review).mockResolvedValue({ candidate: CANDIDATE, republish_task_id: null })
    render(<LegalDocumentPage />)
    fireEvent.click(await screen.findByRole('button', { name: 'Từ chối' }))
    expect(await screen.findByText('Đã lưu quyết định duyệt.')).toBeInTheDocument()
  })
})
