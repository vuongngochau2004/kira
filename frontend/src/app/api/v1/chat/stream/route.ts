import { NextRequest } from 'next/server'

export const runtime = 'nodejs'

export async function GET(req: NextRequest) {
  // Proxy the incoming request to the backend gateway and stream the response back.
  try {
    const incomingUrl = new URL(req.url)
    const qs = incomingUrl.search
    const backendUrl = `${process.env.KIRA_API_URL || 'http://127.0.0.1:8006'}/api/v1/chat/stream${qs}`

    const authHeader = req.headers.get('authorization')
    const headers: Record<string, string> = {
      accept: req.headers.get('accept') || '*/*',
    }
    if (authHeader) {
      headers['authorization'] = authHeader
    }

    const backendResp = await fetch(backendUrl, {
      method: 'GET',
      headers,
    })

    // Forward status and stream body with SSE headers
    const responseHeaders: Record<string, string> = {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    }

    return new Response(backendResp.body, {
      status: backendResp.status,
      headers: responseHeaders,
    })
  } catch (err) {
    return new Response(JSON.stringify({ message: 'Proxy error', error: String(err) }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    })
  }
}

export async function POST(req: NextRequest) {
  // Proxy the incoming request to the backend gateway and stream the response back.
  try {
    const incomingUrl = new URL(req.url)
    const qs = incomingUrl.search
    const backendUrl = `${process.env.KIRA_API_URL || 'http://127.0.0.1:8006'}/api/v1/chat/stream${qs}`

    const authHeader = req.headers.get('authorization')
    const headers: Record<string, string> = {
      accept: req.headers.get('accept') || '*/*',
    }
    if (authHeader) {
      headers['authorization'] = authHeader
    }

    const backendResp = await fetch(backendUrl, {
      method: 'POST',
      headers,
    })

    // Forward status and stream body with SSE headers
    const responseHeaders: Record<string, string> = {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    }

    return new Response(backendResp.body, {
      status: backendResp.status,
      headers: responseHeaders,
    })
  } catch (err) {
    return new Response(JSON.stringify({ message: 'Proxy error', error: String(err) }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    })
  }
}
