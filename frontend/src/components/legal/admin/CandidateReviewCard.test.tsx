import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { RelationCandidate } from '@/lib/legal/types'
import { CandidateReviewCard } from './CandidateReviewCard'

const CANDIDATE: RelationCandidate = {
  id: 'c1',
  legal_document_id: 'd1',
  type: 'AMENDS',
  source_provision_key: '99/2026/QH15#D1.K1',
  target_number: '31/2024/QH15',
  target_provision_ref: 'D3.K1',
  effective_date: '2026-07-01',
  new_text: '1. Nội dung mới.',
  evidence_text: '1. Sửa đổi, bổ sung khoản 1 Điều 3 như sau:',
  evidence_page: 2,
  extractor: 'rule',
  confidence: 0.7,
  status: 'pending',
  flags: [],
  reviewed_by: null,
  reviewed_at: null,
  review_note: null,
}

describe('CandidateReviewCard', () => {
  it('shows the proposal next to its evidence', () => {
    render(<CandidateReviewCard candidate={CANDIDATE} busy={false} onReview={vi.fn()} />)
    expect(screen.getByText('Sửa đổi, bổ sung')).toBeInTheDocument()
    expect(screen.getByText('31/2024/QH15 · D3.K1')).toBeInTheDocument()
    expect(screen.getByText('1. Sửa đổi, bổ sung khoản 1 Điều 3 như sau:')).toBeInTheDocument()
    expect(screen.getByText('1. Nội dung mới.')).toBeInTheDocument()
    expect(screen.getByText('Hiệu lực từ 01/07/2026')).toBeInTheDocument()
  })

  it('approves and rejects with the note', () => {
    const onReview = vi.fn()
    render(<CandidateReviewCard candidate={CANDIDATE} busy={false} onReview={onReview} />)
    fireEvent.change(screen.getByLabelText('Ghi chú duyệt'), { target: { value: 'Đúng' } })
    fireEvent.click(screen.getByRole('button', { name: 'Duyệt' }))
    expect(onReview).toHaveBeenLastCalledWith({ action: 'approve', note: 'Đúng' })
    fireEvent.click(screen.getByRole('button', { name: 'Từ chối' }))
    expect(onReview).toHaveBeenLastCalledWith({ action: 'reject', note: 'Đúng' })
  })

  it('sends only edited fields', () => {
    const onReview = vi.fn()
    render(<CandidateReviewCard candidate={CANDIDATE} busy={false} onReview={onReview} />)
    fireEvent.click(screen.getByRole('button', { name: 'Sửa' }))
    fireEvent.change(screen.getByLabelText('Điều khoản đích'), { target: { value: 'D3.K2' } })
    fireEvent.change(screen.getByLabelText('Ngày hiệu lực'), { target: { value: '2026-08-01' } })
    fireEvent.click(screen.getByRole('button', { name: 'Lưu thay đổi' }))
    expect(onReview).toHaveBeenCalledWith({
      action: 'edit',
      target_provision_ref: 'D3.K2',
      effective_date: '2026-08-01',
    })
  })

  it('cannot approve a candidate whose target is missing', () => {
    render(
      <CandidateReviewCard
        candidate={{ ...CANDIDATE, status: 'unresolved_target' }}
        busy={false}
        onReview={vi.fn()}
      />,
    )
    expect(screen.getByRole('button', { name: 'Duyệt' })).toBeDisabled()
    expect(screen.getByText('Chưa có văn bản đích')).toBeInTheDocument()
  })

  it('disables every action while busy', () => {
    render(<CandidateReviewCard candidate={CANDIDATE} busy onReview={vi.fn()} />)
    for (const name of ['Duyệt', 'Từ chối', 'Sửa']) {
      expect(screen.getByRole('button', { name })).toBeDisabled()
    }
  })
})
