import { beforeEach, describe, expect, it } from 'vitest'
import { useSourcesStore } from './sources-store'

const LEGAL = {
  number: '31/2024/QH15',
  doc_type: 'law',
  provision_key: '31/2024/QH15#D3.K1',
  label: 'Khoản 1',
  title: 'Luật Đất đai',
  valid_from: '2026-07-01',
  valid_to: null,
  amended_after: null,
  role: 'primary' as const,
}

beforeEach(() => {
  useSourcesStore.getState().reset()
})

describe('sources store', () => {
  it('keeps legal data on flat sources', () => {
    useSourcesStore.getState().setSources([
      { chunk_id: 'v1', title: 'Khoản 1 — Luật Đất đai (31/2024/QH15)', snippet: 'Nội dung', legal: LEGAL },
      { chunk_id: 'c1', title: 'quy-che.pdf', snippet: 'Điều 5', document_id: 'doc-1' },
    ])
    const [legal, plain] = useSourcesStore.getState().sources
    expect(legal.legal).toEqual(LEGAL)
    expect(plain.legal).toBeUndefined()
  })
})
