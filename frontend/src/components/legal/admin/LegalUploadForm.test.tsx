import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { LegalDocument, LegalUploadInput } from '@/lib/legal/types'
import { LegalUploadForm } from './LegalUploadForm'

function fill(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } })
}

function fillValidForm() {
  const file = new File(['Điều 1.'], 'luat.pdf', { type: 'application/pdf' })
  fireEvent.change(screen.getByLabelText('Tệp văn bản'), { target: { files: [file] } })
  fill('Số hiệu', '31/2024/QH15')
  fill('Tên văn bản', 'Luật Đất đai')
  fill('Cơ quan ban hành', 'Quốc hội')
  fill('Ngày ban hành', '2024-01-18')
  fill('Ngày hiệu lực', '2024-08-01')
  return file
}

describe('LegalUploadForm', () => {
  it('submits the file with trimmed metadata', async () => {
    const submit = vi.fn(async (input: LegalUploadInput) => ({ id: 'd1', number: input.number }) as LegalDocument)
    const onUploaded = vi.fn()
    render(<LegalUploadForm submit={submit} onUploaded={onUploaded} />)
    const file = fillValidForm()
    fill('Loại văn bản', 'decree')
    fill('Nguồn (URL)', '  https://vbpl.vn/x  ')

    fireEvent.click(screen.getByRole('button', { name: 'Tải lên' }))

    await waitFor(() => expect(onUploaded).toHaveBeenCalled())
    expect(submit).toHaveBeenCalledWith({
      file,
      number: '31/2024/QH15',
      doc_type: 'decree',
      title: 'Luật Đất đai',
      issuer: 'Quốc hội',
      issued_date: '2024-01-18',
      effective_date: '2024-08-01',
      source_url: 'https://vbpl.vn/x',
    })
  })

  it('rejects an effective date before the issued date', async () => {
    const submit = vi.fn()
    render(<LegalUploadForm submit={submit} onUploaded={vi.fn()} />)
    fillValidForm()
    fill('Ngày hiệu lực', '2023-12-31')
    fireEvent.click(screen.getByRole('button', { name: 'Tải lên' }))
    expect(await screen.findByText('Ngày hiệu lực không được trước ngày ban hành.')).toBeInTheDocument()
    expect(submit).not.toHaveBeenCalled()
  })

  it('requires a file', async () => {
    const submit = vi.fn()
    render(<LegalUploadForm submit={submit} onUploaded={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Tải lên' }))
    expect(await screen.findByText('Hãy chọn tệp văn bản.')).toBeInTheDocument()
    expect(submit).not.toHaveBeenCalled()
  })

  it('shows backend errors', async () => {
    const submit = vi.fn(async () => {
      throw new Error('Legal document 31/2024/QH15 already exists')
    })
    render(<LegalUploadForm submit={submit} onUploaded={vi.fn()} />)
    fillValidForm()
    fireEvent.click(screen.getByRole('button', { name: 'Tải lên' }))
    expect(await screen.findByText('Legal document 31/2024/QH15 already exists')).toBeInTheDocument()
  })
})
