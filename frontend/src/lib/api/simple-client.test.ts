import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiErrorMessage, fetchAPI } from './simple-client'

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
