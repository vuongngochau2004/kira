import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiErrorMessage, chatAPI, conversationsAPI, fetchAPI } from './simple-client'
import type { SSEChunk } from './simple-client'

function mockFetch(response: Response) {
  const fn = vi.fn(async () => response)
  vi.stubGlobal('fetch', fn)
  return fn
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('fetchAPI', () => {
  it('parses JSON bodies and sends cookies', async () => {
    const fn = mockFetch(new Response(JSON.stringify({ ok: true }), { status: 200 }))
    await expect(fetchAPI('/api/x')).resolves.toEqual({ ok: true })
    expect((fn.mock.calls[0] as unknown[])[1]).toMatchObject({ credentials: 'include' })
  })

  it('resolves 204 responses to undefined', async () => {
    mockFetch(new Response(null, { status: 204 }))
    await expect(fetchAPI('/api/x', { method: 'DELETE' })).resolves.toBeUndefined()
  })

  it('turns FastAPI validation lists into a readable message', async () => {
    mockFetch(
      new Response(JSON.stringify({ detail: [{ msg: 'Field required' }, { msg: 'Invalid date' }] }), {
        status: 422,
      }),
    )
    await expect(fetchAPI('/api/x')).rejects.toMatchObject({
      message: 'Field required; Invalid date',
      status: 422,
    })
  })
})

describe('apiErrorMessage', () => {
  it('prefers explicit messages and falls back', () => {
    expect(apiErrorMessage({ error: { message: 'Lỗi A' } }, 'x')).toBe('Lỗi A')
    expect(apiErrorMessage({ detail: 'Không tìm thấy' }, 'x')).toBe('Không tìm thấy')
    expect(apiErrorMessage({}, 'Mặc định')).toBe('Mặc định')
    expect(apiErrorMessage(null, 'Mặc định')).toBe('Mặc định')
  })
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
