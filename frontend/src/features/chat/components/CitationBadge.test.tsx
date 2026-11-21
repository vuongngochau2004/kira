import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { parseContentWithCitations } from '@/features/chat/components/CitationBadge'

describe('parseContentWithCitations', () => {
  it('opens the exact verified chunk', () => {
    const onClick = vi.fn()
    render(<>{parseContentWithCitations('Answer [source:chunk-2]', [
      { chunk_id: 'chunk-2', source: 'report.pdf', page_number: 3 },
    ], onClick)}</>)

    fireEvent.click(screen.getByRole('button', { name: /chunk-2/ }))
    expect(onClick).toHaveBeenCalledWith('chunk-2', expect.objectContaining({ page_number: 3 }))
  })

  it('labels an unavailable chunk without an actionable source', () => {
    render(<>{parseContentWithCitations('Answer [source:missing]', [])}</>)
    expect(screen.getByText('Nguồn không còn khả dụng')).toBeInTheDocument()
    expect(screen.queryByRole('button')).toBeNull()
  })
})
