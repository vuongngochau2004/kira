import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { LegalDocument } from '@/lib/legal/types'
import { LegalDocumentTable } from './LegalDocumentTable'

const DOC: LegalDocument = {
  id: 'd1',
  number: '31/2024/QH15',
  doc_type: 'law',
  title: 'Luật Đất đai',
  issuer: 'Quốc hội',
  issued_date: '2024-01-18',
  effective_date: '2024-08-01',
  source_url: null,
  status: 'in_review',
  warnings: ['llm_extraction_incomplete'],
  error_detail: null,
  provision_count: 260,
  published_at: null,
  created_at: '2026-10-15T08:00:00',
}

describe('LegalDocumentTable', () => {
  it('renders one linked row per document', () => {
    render(<LegalDocumentTable documents={[DOC]} />)
    const link = screen.getByRole('link', { name: /31\/2024\/QH15/ })
    expect(link).toHaveAttribute('href', '/admin/legal/d1')
    expect(screen.getByText('Luật Đất đai')).toBeInTheDocument()
    expect(screen.getByText('Chờ duyệt')).toBeInTheDocument()
    expect(screen.getByText('Hiệu lực 01/08/2024')).toBeInTheDocument()
    expect(screen.getByText('260 điều khoản')).toBeInTheDocument()
    expect(screen.getByText('1 cảnh báo')).toBeInTheDocument()
  })

  it('shows an empty state', () => {
    render(<LegalDocumentTable documents={[]} />)
    expect(screen.getByText('Chưa có văn bản pháp luật nào.')).toBeInTheDocument()
  })
})
