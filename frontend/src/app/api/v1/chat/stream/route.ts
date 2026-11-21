import { NextRequest } from 'next/server'
import { getBackendUrl } from '@/lib/api/backend-url'

const BACKEND_URL = getBackendUrl()

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'

export async function POST(req: NextRequest) {
  const upstreamController = new AbortController()
  const cancelUpstream = (): void => upstreamController.abort()
  req.signal.addEventListener('abort', cancelUpstream, { once: true })
  if (req.signal.aborted) cancelUpstream()
  try {
    const body = await req.json()
    const { message, conversation_id } = body

    if (!message) {
      req.signal.removeEventListener('abort', cancelUpstream)
      return new Response(JSON.stringify({ error: 'Message is required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    // Build URL with query params for backward compatibility
    const url = new URL(`${BACKEND_URL}/api/v1/chat/stream`)
    if (conversation_id) {
      url.searchParams.set('conversation_id', conversation_id)
    }

    // Forward request to backend with streaming
    const response = await fetch(url.toString(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Forward cookies from client
        'Cookie': req.headers.get('cookie') || '',
      },
      body: JSON.stringify({ message, conversation_id }),
      cache: 'no-store',
      signal: upstreamController.signal,
    })

    if (!response.ok) {
      req.signal.removeEventListener('abort', cancelUpstream)
      const errorText = await response.text()
      return new Response(errorText, {
        status: response.status,
        headers: { 'Content-Type': 'text/plain' },
      })
    }

    if (!response.body) {
      req.signal.removeEventListener('abort', cancelUpstream)
      return new Response('No response body', { status: 500 })
    }

    const reader = response.body.getReader()
    const streamedBody = new ReadableStream<Uint8Array>({
      async pull(controller): Promise<void> {
        try {
          const { done, value } = await reader.read()
          if (done) {
            req.signal.removeEventListener('abort', cancelUpstream)
            controller.close()
          } else {
            controller.enqueue(value)
          }
        } catch (error) {
          req.signal.removeEventListener('abort', cancelUpstream)
          if (upstreamController.signal.aborted) {
            controller.close()
          } else {
            controller.error(error)
          }
        }
      },
      async cancel(reason: unknown): Promise<void> {
        cancelUpstream()
        req.signal.removeEventListener('abort', cancelUpstream)
        try {
          await reader.cancel(reason)
        } catch {
          // Abort may already have closed the upstream reader.
        }
      },
    })

    return new Response(streamedBody, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache, no-transform',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no', // Disable nginx buffering
      },
    })
  } catch {
    req.signal.removeEventListener('abort', cancelUpstream)
    if (upstreamController.signal.aborted) {
      return new Response(null, { status: 499 })
    }
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    })
  }
}
