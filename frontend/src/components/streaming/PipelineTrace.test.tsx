import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { PipelineTrace } from './PipelineTrace'

const STEPS = [
  { stage: 'classify', metadata: { intent: 'rag', confidence: 0.5 } },
  { stage: 'retrieval', metadata: { docs_retrieved: 3, refined_queries: ['q'], duration_ms: 600 } },
  { stage: 'quality', metadata: { quality_score: 0.78, decision: 'pass', duration_ms: 1400 } },
]

describe('PipelineTrace', () => {
  it('shows every step while the answer is streaming', () => {
    render(<PipelineTrace steps={STEPS} isStreaming />)
    expect(screen.getByText('Phân loại ý định')).toBeInTheDocument()
    expect(screen.getByText('3 tài liệu · 1 truy vấn')).toBeInTheDocument()
    expect(screen.getByText('Đang xử lý bước tiếp theo…')).toBeInTheDocument()
  })

  it('is collapsed after streaming and expands on click', () => {
    render(<PipelineTrace steps={STEPS} isStreaming={false} />)
    expect(screen.queryByText('Kiểm định chất lượng')).not.toBeInTheDocument()
    expect(screen.getByText(/3 bước · 2\.0s/)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button'))
    expect(screen.getByText('Kiểm định chất lượng')).toBeInTheDocument()
    expect(screen.getByText('điểm 0.78 · đạt')).toBeInTheDocument()
  })
})
