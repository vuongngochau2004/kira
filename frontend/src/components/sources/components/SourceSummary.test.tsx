import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SourceSummary } from './SourceSummary'

describe('SourceSummary', () => {
  it('shows a compact source row with an accessible expand action', () => {
    const onExpand = vi.fn()
    render(
      <SourceSummary
        title="A very long source document name.pdf"
        type="pdf"
        referenceCount={2}
        expanded={false}
        onExpand={onExpand}
      />
    )

    const button = screen.getByRole('button', { name: /A very long source document name.pdf/ })
    expect(button).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByText(/2 trích dẫn/)).toBeInTheDocument()
    fireEvent.click(button)
    expect(onExpand).toHaveBeenCalledOnce()
  })
})
