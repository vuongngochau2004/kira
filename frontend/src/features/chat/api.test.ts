import { afterEach, describe, expect, it, vi } from 'vitest'
import { chatAPI, conversationsAPI } from '@/features/chat/api'
import type { SSEChunk } from '@/features/chat/api'

function mockFetch(response: Response) {
  const fn = vi.fn(async () => response)
  vi.stubGlobal('fetch', fn)
  return fn
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('conversationsAPI.list', () => {
  it('uses backend limit/offset and searches across all pages', async () => {
    const fn = mockFetch(new Response(JSON.stringify({
      total: 1,
      limit: 20,
      offset: 20,
      conversations: [{ id: 'conversation-1', title: 'Hợp đồng' }],
    }), { status: 200 }))

    const result = await conversationsAPI.list(2, 20, 'hợp đồng')

    expect(result).toMatchObject({ total: 1, page: 2, page_size: 20 })
    expect(result.items).toHaveLength(1)
    const requestUrl = new URL(String((fn.mock.calls[0] as unknown[])[0]), 'http://localhost')
    expect(requestUrl.searchParams.get('limit')).toBe('20')
    expect(requestUrl.searchParams.get('offset')).toBe('20')
    expect(requestUrl.searchParams.get('search')).toBe('hợp đồng')
  })
})

describe('chatAPI.streamMessage', () => {
  it('parses provisional and replacement events and skips malformed content', async () => {
    const body = [
      { type: 'content', data: { text: 'Draft', provisional: true, attempt: 1 } },
      { type: 'content_replace', data: { text: 'Final', provisional: false } },
      { type: 'content_replace', data: { text: 42 } },
      { type: 'done' },
    ].map((event) => `data: ${JSON.stringify(event)}\n\n`).join('')
    mockFetch(new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } }))

    const events: SSEChunk[] = []
    for await (const event of chatAPI.streamMessage('Question')) events.push(event)
    expect(events.map((event) => event.type)).toEqual(['content', 'content_replace', 'done'])
  })
})
