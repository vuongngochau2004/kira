import { describe, expect, it } from 'vitest'
import { createStreamingStateBuilder, ensureFlatSources } from './index'

const LEGAL_CITATION = {
  filename: 'Khoản 1 — Luật Đất đai (31/2024/QH15)',
  text: '1. Nội dung.',
  confidence: 0.6,
  chunk_id: 'v1',
  legal: {
    number: '31/2024/QH15',
    doc_type: 'law',
    provision_key: '31/2024/QH15#D3.K1',
    label: 'Khoản 1',
    title: 'Luật Đất đai',
    valid_from: '2026-07-01',
    valid_to: null,
    amended_after: null,
    role: 'primary' as const,
  },
}

describe('StreamingStateBuilder legal data', () => {
  it('records the applied date from the temporal status event', () => {
    const builder = createStreamingStateBuilder()
    builder.processChunk('status', {
      stage: 'temporal',
      metadata: { mode: 'single', dates: ['2026-10-15'], source: 'rule' },
    })
    expect(builder.getState().legal).toEqual({
      mode: 'single',
      dates: ['2026-10-15'],
      temporal_source: 'rule',
      notices: [],
    })
  })

  it('ignores other status stages', () => {
    const builder = createStreamingStateBuilder()
    builder.processChunk('status', { stage: 'retrieval', metadata: { sources: 3 } })
    expect(builder.getState().legal).toBeNull()
  })

  it('keeps legal citations and answer notices from the metadata event', () => {
    const builder = createStreamingStateBuilder()
    builder.processChunk('metadata', {
      citations: [LEGAL_CITATION],
      legal: { mode: 'single', dates: ['2026-10-15'], temporal_source: 'rule', notices: ['Ghi chú'] },
    })
    const state = builder.getState()
    expect(state.sources[0].legal).toEqual(LEGAL_CITATION.legal)
    expect(state.legal?.notices).toEqual(['Ghi chú'])
  })

  it('drops the applied date when the legal answer failed', () => {
    const builder = createStreamingStateBuilder()
    builder.processChunk('status', {
      stage: 'temporal',
      metadata: { mode: 'single', dates: ['2026-10-15'], source: 'rule' },
    })
    builder.processChunk('metadata', { citations: [], legal: { error: 'unavailable' } })
    expect(builder.getState().legal).toBeNull()
  })

  it('ignores an error-shaped legal object', () => {
    const builder = createStreamingStateBuilder()
    builder.processChunk('metadata', { citations: [], legal: { error: 'unavailable' } })
    expect(builder.getState().legal).toBeNull()
  })
})

describe('ensureFlatSources', () => {
  it('passes legal data through and leaves ordinary citations unchanged', () => {
    const [legal, plain] = ensureFlatSources([
      LEGAL_CITATION,
      { filename: 'quy-che.pdf', text: 'Điều 5', document_id: 'doc-1', chunk_index: 2 },
    ]) as Record<string, unknown>[]
    expect(legal.legal).toEqual(LEGAL_CITATION.legal)
    expect(legal.title).toBe(LEGAL_CITATION.filename)
    expect('legal' in plain).toBe(false)
    expect(plain.document_id).toBe('doc-1')
  })
})
