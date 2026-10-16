import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { LegalAnswerNote } from './LegalAnswerNote'

describe('LegalAnswerNote', () => {
  it('shows the applied date', () => {
    render(<LegalAnswerNote info={{ mode: 'single', dates: ['2026-10-15'], notices: [] }} />)
    expect(screen.getByText('Áp dụng tại ngày 15/10/2026')).toBeInTheDocument()
  })

  it('shows both dates of a comparison and every notice', () => {
    render(
      <LegalAnswerNote
        info={{ mode: 'compare', dates: ['2026-06-30', '2026-07-01'], notices: ['Chưa kiểm tra được văn bản liên quan.'] }}
      />,
    )
    expect(screen.getByText('So sánh quy định ngày 30/06/2026 và ngày 01/07/2026')).toBeInTheDocument()
    expect(screen.getByText('Chưa kiểm tra được văn bản liên quan.')).toBeInTheDocument()
  })
})
