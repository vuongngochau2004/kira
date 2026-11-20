import { afterEach, describe, expect, it, vi } from 'vitest'
import { NextRequest } from 'next/server'
import { POST } from './route'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('chat stream proxy', () => {
  it('aborts the upstream fetch when the browser request is aborted', async () => {
    const browserController = new AbortController()
    let upstreamSignal: AbortSignal | undefined
    const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
      upstreamSignal = init.signal as AbortSignal
      return new Response(new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(new TextEncoder().encode('data: {"type":"content"}\n\n'))
        },
      }), { status: 200 })
    })
    vi.stubGlobal('fetch', fetchMock)

    const req = new NextRequest('http://localhost/api/v1/chat/stream', {
      method: 'POST',
      body: JSON.stringify({ message: 'Question' }),
    })
    Object.defineProperty(req, 'signal', { value: browserController.signal })
    const response = await POST(req)
    expect(response.status).toBe(200)
    const reader = response.body?.getReader()
    await reader?.read()
    browserController.abort()
    expect(upstreamSignal?.aborted).toBe(true)
    await reader?.cancel()
  })

  it('aborts the upstream fetch when the downstream reader closes', async () => {
    let upstreamSignal: AbortSignal | undefined
    vi.stubGlobal('fetch', vi.fn(async (_url: string, init: RequestInit) => {
      upstreamSignal = init.signal as AbortSignal
      return new Response(new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(new TextEncoder().encode('data: {"type":"content"}\n\n'))
        },
      }), { status: 200 })
    }))

    const req = new NextRequest('http://localhost/api/v1/chat/stream', {
      method: 'POST',
      body: JSON.stringify({ message: 'Question' }),
    })
    const response = await POST(req)
    const reader = response.body?.getReader()
    await reader?.read()
    await reader?.cancel()
    expect(upstreamSignal?.aborted).toBe(true)
  })
})
