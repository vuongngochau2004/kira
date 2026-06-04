import { NextRequest } from 'next/server'

const BACKEND_URL = process.env.KIRA_API_URL || 'http://127.0.0.1:8006'

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { message, conversation_id } = body

    if (!message) {
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
    })

    if (!response.ok) {
      const errorText = await response.text()
      return new Response(errorText, {
        status: response.status,
        headers: { 'Content-Type': 'text/plain' },
      })
    }

    // Stream the response
    const reader = response.body?.getReader()
    if (!reader) {
      return new Response('No response body', { status: 500 })
    }

    // Create a TransformStream to process and forward chunks
    const stream = new ReadableStream({
      async start(controller) {
        const decoder = new TextDecoder()
        try {
          while (true) {
            const { done, value } = await reader.read()
            if (done) break

            // Forward raw bytes directly
            controller.enqueue(value)
          }
          controller.close()
        } catch (error) {
          controller.error(error)
        }
      },
    })

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no', // Disable nginx buffering
      },
    })
  } catch (error) {
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    })
  }
}
