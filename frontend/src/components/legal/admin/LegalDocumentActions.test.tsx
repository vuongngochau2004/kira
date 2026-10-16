import { describe, expect, it } from 'vitest'
import type { LegalDocument } from '@/lib/legal/types'
import { documentActionState } from './LegalDocumentActions'

const base = {
  id: 'd1',
  provision_count: 10,
  published_at: null,
} as unknown as LegalDocument

const state = (overrides: Partial<LegalDocument>) => documentActionState({ ...base, ...overrides })

describe('documentActionState', () => {
  it('allows publishing reviewed, published or failed documents with provisions', () => {
    expect(state({ status: 'in_review' }).canPublish).toBe(true)
    expect(state({ status: 'published', published_at: '2026-07-01T00:00:00' }).canPublish).toBe(true)
    expect(state({ status: 'failed' }).canPublish).toBe(true)
    expect(state({ status: 'failed', provision_count: 0 }).canPublish).toBe(false)
    expect(state({ status: 'parsing' }).canPublish).toBe(false)
  })

  it('allows reprocessing only uploaded or failed documents', () => {
    expect(state({ status: 'uploaded' }).canReprocess).toBe(true)
    expect(state({ status: 'failed' }).canReprocess).toBe(true)
    expect(state({ status: 'in_review' }).canReprocess).toBe(false)
  })

  it('never allows deleting a document that was published', () => {
    expect(state({ status: 'failed' }).canDelete).toBe(true)
    expect(state({ status: 'failed', published_at: '2026-07-01T00:00:00' }).canDelete).toBe(false)
    expect(state({ status: 'published', published_at: '2026-07-01T00:00:00' }).canDelete).toBe(false)
    expect(state({ status: 'publishing' }).canDelete).toBe(false)
  })
})
