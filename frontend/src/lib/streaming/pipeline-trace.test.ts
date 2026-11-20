import { describe, expect, it } from 'vitest'
import {
  createStreamingStateBuilder,
  describePipelineStep,
  formatDuration,
  hasGraphSteps,
  toPipelineSteps,
  totalDurationMs,
} from './index'

describe('StreamingStateBuilder pipeline trace', () => {
  it('records classification and every graph node in order', () => {
    const builder = createStreamingStateBuilder()
    builder.processChunk('routing', { router: 'agentic_rag', intent: 'rag', confidence: 0.5 })
    builder.processChunk('status', { stage: 'retrieval', metadata: { docs_retrieved: 2 } })
    builder.processChunk('status', { stage: 'quality', metadata: { decision: 'regenerate' } })

    expect(builder.getState().pipeline.map((step) => step.stage)).toEqual([
      'classify',
      'retrieval',
      'quality',
    ])
  })

  it('keeps a single classify step when routing is sent twice', () => {
    const builder = createStreamingStateBuilder()
    builder.processChunk('routing', { router: 'RAGHandler', intent: 'rag', confidence: 0.85 })
    builder.processChunk('routing', { router: 'agentic_rag', intent: 'rag' })
    const { pipeline } = builder.getState()
    expect(pipeline).toHaveLength(1)
    expect(pipeline[0].metadata).toMatchObject({ router: 'agentic_rag', confidence: 0.85 })
  })

  it('starts empty again after reset', () => {
    const builder = createStreamingStateBuilder()
    builder.processChunk('status', { stage: 'generation', metadata: {} })
    builder.reset()
    expect(builder.getState().pipeline).toEqual([])
  })

  it('updates started retrieval and quality steps when they complete', () => {
    const builder = createStreamingStateBuilder()
    builder.processChunk('status', { stage: 'retrieval', metadata: { state: 'started' } })
    builder.processChunk('status', { stage: 'retrieval', metadata: { duration_ms: 300, docs_retrieved: 2 } })
    builder.processChunk('status', { stage: 'quality', metadata: { state: 'started' } })
    builder.processChunk('status', { stage: 'quality', metadata: { duration_ms: 400, decision: 'pass' } })

    expect(builder.getState().pipeline).toEqual([
      { stage: 'retrieval', metadata: { state: 'completed', duration_ms: 300, docs_retrieved: 2 } },
      { stage: 'quality', metadata: { state: 'completed', duration_ms: 400, decision: 'pass' } },
    ])
  })

  it('keeps regeneration attempts as separate steps while merging each generation completion', () => {
    const builder = createStreamingStateBuilder()
    builder.processChunk('status', { stage: 'generation', metadata: { attempt: 1 } })
    builder.processChunk('status', { stage: 'generation', metadata: { iteration: 0, duration_ms: 100 } })
    builder.processChunk('status', { stage: 'quality', metadata: { state: 'started' } })
    builder.processChunk('status', { stage: 'quality', metadata: { decision: 'regenerate' } })
    builder.processChunk('status', { stage: 'generation', metadata: { attempt: 2 } })
    builder.processChunk('status', { stage: 'generation', metadata: { iteration: 1, duration_ms: 120 } })

    expect(builder.getState().pipeline).toHaveLength(3)
    expect(builder.getState().pipeline.map((step) => step.stage)).toEqual([
      'generation', 'quality', 'generation',
    ])
    expect(builder.getState().pipeline[2].metadata).toMatchObject({
      attempt: 2, iteration: 1, duration_ms: 120, state: 'completed',
    })
  })
})

describe('pipeline trace helpers', () => {
  it('drops malformed persisted steps', () => {
    expect(toPipelineSteps(null)).toBeUndefined()
    expect(toPipelineSteps([{ stage: '' }, 'x', { metadata: {} }])).toBeUndefined()
    expect(toPipelineSteps([{ stage: 'quality' }])).toEqual([{ stage: 'quality', metadata: {} }])
  })

  it('needs at least one graph node to be worth rendering', () => {
    expect(hasGraphSteps([{ stage: 'classify', metadata: {} }])).toBe(false)
    expect(hasGraphSteps([{ stage: 'classify', metadata: {} }, { stage: 'retrieval', metadata: {} }])).toBe(true)
  })

  it('sums and formats durations', () => {
    const steps = [
      { stage: 'retrieval', metadata: { duration_ms: 600 } },
      { stage: 'generation', metadata: { duration_ms: 4500 } },
    ]
    expect(totalDurationMs(steps)).toBe(5100)
    expect(formatDuration(600)).toBe('600ms')
    expect(formatDuration(5100)).toBe('5.1s')
  })

  it('describes the quality gate decision and issues', () => {
    const view = describePipelineStep({
      stage: 'quality',
      metadata: { quality_score: 0.62, decision: 'regenerate', issues: ['Response too short'] },
    })
    expect(view.label).toBe('Kiểm định chất lượng')
    expect(view.detail).toBe('điểm 0.62 · chưa đạt → sinh lại')
    expect(view.tone).toBe('warning')
    expect(view.notes).toEqual(['Response too short'])
  })

  it('shows pending graph steps without premature zero-document warnings', () => {
    const retrieval = describePipelineStep({ stage: 'retrieval', metadata: { state: 'started' } })
    const quality = describePipelineStep({ stage: 'quality', metadata: { state: 'started' } })
    const generation = describePipelineStep({ stage: 'generation', metadata: { attempt: 2 } })

    for (const view of [retrieval, quality, generation]) {
      expect(view).toMatchObject({ detail: 'Đang xử lý…', pending: true, tone: 'success' })
      expect(view.notes).toEqual([])
    }
  })

  it('labels a regeneration pass by its iteration', () => {
    const view = describePipelineStep({ stage: 'generation', metadata: { iteration: 1, response_length: 387 } })
    expect(view.label).toBe('Sinh lại câu trả lời (lần 1)')
    expect(view.detail).toBe('387 ký tự')
  })
})
