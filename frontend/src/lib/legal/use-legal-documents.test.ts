import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { legalAPI } from '@/lib/api/legal-client'
import type { LegalDocument } from './types'
import { useLegalDocuments } from './use-legal-documents'

vi.mock('@/lib/api/legal-client', () => ({ legalAPI: { listDocuments: vi.fn() } }))

const doc = (status: LegalDocument['status']) => ({ id: 'd1', status }) as LegalDocument

beforeEach(() => {
  vi.mocked(legalAPI.listDocuments).mockReset()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useLegalDocuments', () => {
  it('loads documents and reports errors', async () => {
    vi.mocked(legalAPI.listDocuments).mockRejectedValueOnce(new Error('Không tải được'))
    const { result } = renderHook(() => useLegalDocuments(1000))
    await waitFor(() => expect(result.current.error).toBe('Không tải được'))
    vi.mocked(legalAPI.listDocuments).mockResolvedValueOnce([doc('published')])
    await act(async () => {
      await result.current.reload()
    })
    expect(result.current.documents).toHaveLength(1)
    expect(result.current.error).toBeNull()
  })

  it('polls only while a document is still being processed', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.mocked(legalAPI.listDocuments)
      .mockResolvedValueOnce([doc('parsing')])
      .mockResolvedValue([doc('in_review')])
    renderHook(() => useLegalDocuments(1000))
    await waitFor(() => expect(legalAPI.listDocuments).toHaveBeenCalledTimes(1))
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1100)
    })
    expect(legalAPI.listDocuments).toHaveBeenCalledTimes(2)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000)
    })
    expect(legalAPI.listDocuments).toHaveBeenCalledTimes(2)
  })
})
