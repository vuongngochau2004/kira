import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { legalAPI } from '@/lib/api/legal-client'
import { LegalCitationMeta } from './LegalCitationMeta'
import { LegalValidityBadge } from './LegalValidityBadge'

vi.mock('@/lib/api/legal-client', () => ({
  legalAPI: { provisionHistory: vi.fn() },
}))

const LEGAL = {
  number: '31/2024/QH15',
  doc_type: 'law',
  provision_key: '31/2024/QH15#D3.K1',
  label: 'Khoản 1',
  title: 'Luật Đất đai',
  valid_from: '2024-08-01',
  valid_to: '2026-07-01',
  amended_after: '2026-07-01',
  role: 'primary' as const,
}

beforeEach(() => {
  vi.mocked(legalAPI.provisionHistory).mockReset()
})

describe('LegalValidityBadge', () => {
  it('shows the validity interval and whether it is in force today', () => {
    const { rerender } = render(<LegalValidityBadge legal={LEGAL} today="2025-01-01" />)
    expect(screen.getByTestId('legal-validity')).toHaveTextContent('Hiệu lực 01/08/2024 → 01/07/2026')
    expect(screen.getByTestId('legal-validity')).toHaveAttribute('data-in-force', 'true')
    rerender(<LegalValidityBadge legal={LEGAL} today="2026-10-15" />)
    expect(screen.getByTestId('legal-validity')).toHaveAttribute('data-in-force', 'false')
  })

  it('warns about a later amendment', () => {
    render(<LegalValidityBadge legal={LEGAL} today="2025-01-01" />)
    expect(screen.getByTestId('legal-amended')).toHaveTextContent('Đã sửa đổi từ 01/07/2026')
  })

  it('omits the amendment warning when there is none', () => {
    render(<LegalValidityBadge legal={{ ...LEGAL, amended_after: null }} today="2025-01-01" />)
    expect(screen.queryByTestId('legal-amended')).toBeNull()
  })
})

describe('LegalCitationMeta', () => {
  it('shows the role and opens the provision history', async () => {
    vi.mocked(legalAPI.provisionHistory).mockResolvedValue({
      provision_key: LEGAL.provision_key,
      label: 'Khoản 1',
      number: '31/2024/QH15',
      title: 'Luật Đất đai',
      doc_type: 'law',
      versions: [
        { version_id: 'v0', text: '1. Nội dung cũ.', page: 3, valid_from: '2024-08-01', valid_to: '2026-07-01' },
        { version_id: 'v1', text: '1. Nội dung mới.', page: null, valid_from: '2026-07-01', valid_to: null },
      ],
      in_force: { version_id: 'v1', text: '1. Nội dung mới.', page: null, valid_from: '2026-07-01', valid_to: null },
    })
    render(<LegalCitationMeta legal={LEGAL} today="2025-01-01" />)
    expect(screen.getByText('Quy định áp dụng')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Xem lịch sử hiệu lực' }))

    expect(await screen.findByText('1. Nội dung cũ.')).toBeInTheDocument()
    expect(screen.getByText('1. Nội dung mới.')).toBeInTheDocument()
    expect(screen.getByText('Đang áp dụng')).toBeInTheDocument()
    expect(legalAPI.provisionHistory).toHaveBeenCalledWith('31/2024/QH15#D3.K1')
  })

  it('shows an error when the history cannot be loaded', async () => {
    vi.mocked(legalAPI.provisionHistory).mockRejectedValue(new Error('Không tìm thấy'))
    render(<LegalCitationMeta legal={LEGAL} today="2025-01-01" />)
    fireEvent.click(screen.getByRole('button', { name: 'Xem lịch sử hiệu lực' }))
    expect(await screen.findByText('Không tìm thấy')).toBeInTheDocument()
  })
})
