import { afterEach, describe, expect, it, vi } from 'vitest'

import { demoClassification, demoExtraction, demoReranking } from '@/features/admin/pipeline-lab-api'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('pipeline lab client', () => {
  it('uploads the original file as multipart form data', async () => {
    const file = new File(['image'], 'sample.png', { type: 'image/png' })
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      success: true,
      text: 'recognized',
      confidence: 0.9,
      metadata: {},
      error: null,
      latency_ms: 42,
    }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    const result = await demoExtraction(file)

    expect(result.text).toBe('recognized')
    const [, options] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(options.body).toBeInstanceOf(FormData)
    expect((options.body as FormData).get('file')).toBe(file)
    expect(options.headers).toBeUndefined()
  })

  it('sends a classifier query with cookies', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      intent: 'rag',
      confidence: 0.8,
      reason: 'keyword',
      metadata: {},
      latency_ms: 10,
    }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    const result = await demoClassification('Find my document')

    expect(result.intent).toBe('rag')
    const [, options] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(options.credentials).toBe('include')
    expect(JSON.parse(options.body as string)).toEqual({ query: 'Find my document' })
  })

  it('sends rerank candidates and top K', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      mode: 'tei',
      fallback: false,
      latency_ms: 25,
      results: [{ id: '2', text: 'second', rerank_score: 0.9 }],
    }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    const result = await demoReranking('query', ['first', 'second'], 1)

    expect(result.results[0].rerank_score).toBe(0.9)
    const [, options] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(JSON.parse(options.body as string)).toEqual({
      query: 'query',
      documents: ['first', 'second'],
      top_k: 1,
    })
  })
})
