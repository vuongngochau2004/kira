import { afterEach, describe, expect, it, vi } from 'vitest'
import { legalAPI } from './legal-client'

function mockFetch(body: unknown, status = 200) {
  const fn = vi.fn(
    async () =>
      new Response(body === null ? null : JSON.stringify(body), {
        status,
        headers: { 'Content-Type': 'application/json' },
      }),
  )
  vi.stubGlobal('fetch', fn)
  return fn
}

function call(fn: ReturnType<typeof mockFetch>, index = 0) {
  return fn.mock.calls[index] as unknown as [string, RequestInit]
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('legalAPI', () => {
  it('lists documents with an optional status filter', async () => {
    const fn = mockFetch([])
    await legalAPI.listDocuments('in_review')
    await legalAPI.listDocuments()
    expect(call(fn, 0)[0]).toBe('/api/v1/legal/documents?status=in_review')
    expect(call(fn, 1)[0]).toBe('/api/v1/legal/documents')
  })

  it('uploads metadata and the file as multipart form data', async () => {
    const fn = mockFetch({ id: 'd1' }, 201)
    const file = new File(['Điều 1.'], 'luat.txt', { type: 'text/plain' })
    await legalAPI.upload({
      file,
      number: '31/2024/QH15',
      doc_type: 'law',
      title: 'Luật Đất đai',
      issuer: 'Quốc hội',
      issued_date: '2024-01-18',
      effective_date: '2024-08-01',
      source_url: '',
    })
    const [url, init] = call(fn)
    expect(url).toBe('/api/v1/legal/documents')
    expect(init.method).toBe('POST')
    const form = init.body as FormData
    expect(form.get('number')).toBe('31/2024/QH15')
    expect(form.get('effective_date')).toBe('2024-08-01')
    expect(form.get('file')).toBeInstanceOf(File)
    expect(form.has('source_url')).toBe(false)
  })

  it('reports upload errors from FastAPI', async () => {
    mockFetch({ detail: 'Legal document 31/2024/QH15 already exists' }, 409)
    await expect(
      legalAPI.upload({
        file: new File(['x'], 'a.txt'),
        number: '31/2024/QH15',
        doc_type: 'law',
        title: 't',
        issuer: 'i',
        issued_date: '2024-01-01',
        effective_date: '2024-01-01',
      }),
    ).rejects.toMatchObject({ message: 'Legal document 31/2024/QH15 already exists', status: 409 })
  })

  it('sends review decisions as PATCH JSON', async () => {
    const fn = mockFetch({ candidate: {}, republish_task_id: null })
    await legalAPI.review('c1', { action: 'edit', target_provision_ref: 'D3.K2' })
    const [url, init] = call(fn)
    expect(url).toBe('/api/v1/legal/candidates/c1')
    expect(init.method).toBe('PATCH')
    expect(JSON.parse(init.body as string)).toEqual({ action: 'edit', target_provision_ref: 'D3.K2' })
  })

  it('publishes, reprocesses and deletes', async () => {
    const fn = mockFetch({ document_id: 'd1', task_id: 't1' }, 202)
    await legalAPI.publish('d1')
    await legalAPI.reprocess('d1')
    expect(call(fn, 0)[0]).toBe('/api/v1/legal/documents/d1/publish')
    expect(call(fn, 1)[0]).toBe('/api/v1/legal/documents/d1/reprocess')
    mockFetch(null, 204)
    await expect(legalAPI.remove('d1')).resolves.toBeUndefined()
  })

  it('encodes provision keys containing slashes and hashes', async () => {
    const fn = mockFetch({ versions: [] })
    await legalAPI.provisionHistory('31/2024/QH15#D3.K1', '2026-08-01')
    expect(call(fn)[0]).toBe(
      '/api/v1/legal/provisions?key=31%2F2024%2FQH15%23D3.K1&date=2026-08-01',
    )
  })
})
