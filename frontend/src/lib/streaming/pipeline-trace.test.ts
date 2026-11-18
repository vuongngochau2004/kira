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

  it('labels a regeneration pass by its iteration', () => {
    const view = describePipelineStep({ stage: 'generation', metadata: { iteration: 1, response_length: 387 } })
    expect(view.label).toBe('Sinh lại câu trả lời (lần 1)')
    expect(view.detail).toBe('387 ký tự')
  })
})
