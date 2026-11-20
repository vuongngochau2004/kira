import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SourceCitation } from './SourceCitation'

describe('SourceCitation', () => {
  it('groups chunks by document and opens the source list', () => {
    const onClick = vi.fn()
    render(<SourceCitation sources={[
      { id: 'chunk-1', document_id: 'doc-1', title: 'alpha.pdf', content: 'A', score: 0.9 },
      { id: 'chunk-2', document_id: 'doc-1', title: 'alpha.pdf', content: 'B', score: 0.8 },
      { id: 'chunk-3', document_id: 'doc-2', title: 'beta.pdf', content: 'C', score: 0.7 },
    ]} onClick={onClick} />)

    const button = screen.getByRole('button', { name: /2 tài liệu.*3 trích dẫn/ })
    expect(screen.getByText('2 nguồn')).toBeInTheDocument()
    fireEvent.click(button)
    expect(onClick).toHaveBeenCalledOnce()
  })
})
