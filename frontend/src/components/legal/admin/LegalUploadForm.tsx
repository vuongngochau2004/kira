'use client'

import { useRef, useState, type FormEvent } from 'react'
import { Globe, Link as LinkIcon, Loader2, Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { legalAPI } from '@/lib/api/legal-client'
import { DOC_TYPE_LABELS } from '@/lib/legal/format'
import type { LegalDocType, LegalDocument, LegalUploadInput } from '@/lib/legal/types'

interface LegalUploadFormProps {
  onUploaded: (document: LegalDocument) => void
  submit?: (input: LegalUploadInput) => Promise<LegalDocument>
  submitFromUrl?: (url: string) => Promise<LegalDocument>
}

const EMPTY = {
  number: '',
  doc_type: 'law' as LegalDocType,
  title: '',
  issuer: '',
  issued_date: '',
  effective_date: '',
  source_url: '',
}

const ACCEPTED_FILES = '.pdf,.docx,.txt,.md,.html'

export function LegalUploadForm({
  onUploaded,
  submit = legalAPI.upload,
  submitFromUrl = legalAPI.uploadFromUrl,
}: LegalUploadFormProps) {
  const [mode, setMode] = useState<'file' | 'url'>('file')
  const [urlInput, setUrlInput] = useState('')
  const [values, setValues] = useState(EMPTY)
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  const update = (field: keyof typeof EMPTY) => (value: string) =>
    setValues((current) => ({ ...current, [field]: value }))

  const validateFile = (): string | null => {
    if (!file) return 'Hãy chọn tệp văn bản.'
    if (!values.number.trim() || !values.title.trim() || !values.issuer.trim()) {
      return 'Hãy nhập đủ số hiệu, tên văn bản và cơ quan ban hành.'
    }
    if (!values.issued_date || !values.effective_date) return 'Hãy nhập ngày ban hành và ngày hiệu lực.'
    if (values.effective_date < values.issued_date) return 'Ngày hiệu lực không được trước ngày ban hành.'
    return null
  }

  const handleFileSubmit = async (event: FormEvent) => {
    event.preventDefault()
    const problem = validateFile()
    if (problem || !file) {
      setError(problem)
      return
    }
    setIsSubmitting(true)
    setError(null)
    try {
      const document = await submit({
        file,
        number: values.number.trim(),
        doc_type: values.doc_type,
        title: values.title.trim(),
        issuer: values.issuer.trim(),
        issued_date: values.issued_date,
        effective_date: values.effective_date,
        source_url: values.source_url.trim(),
      })
      setValues(EMPTY)
      setFile(null)
      if (fileInput.current) fileInput.current.value = ''
      onUploaded(document)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Tải lên thất bại')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleUrlSubmit = async (event: FormEvent) => {
    event.preventDefault()
    const cleanUrl = urlInput.trim()
    if (!cleanUrl) {
      setError('Vui lòng nhập đường dẫn văn bản từ vbpl.vn.')
      return
    }
    if (!cleanUrl.startsWith('http://') && !cleanUrl.startsWith('https://')) {
      setError('Đường dẫn phải bắt đầu bằng http:// hoặc https://')
      return
    }
    setIsSubmitting(true)
    setError(null)
    try {
      const document = await submitFromUrl(cleanUrl)
      setUrlInput('')
      onUploaded(document)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Thu thập từ liên kết thất bại')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex rounded-md border border-input p-0.5 bg-muted/40 text-xs">
        <button
          type="button"
          onClick={() => { setMode('file'); setError(null); }}
          className={`flex-1 py-1.5 px-3 rounded text-center font-medium transition-colors ${
            mode === 'file' ? 'bg-background shadow-xs text-foreground' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <Upload className="inline-block h-3.5 w-3.5 mr-1" />
          Tải lên tệp
        </button>
        <button
          type="button"
          onClick={() => { setMode('url'); setError(null); }}
          className={`flex-1 py-1.5 px-3 rounded text-center font-medium transition-colors ${
            mode === 'url' ? 'bg-background shadow-xs text-foreground' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <Globe className="inline-block h-3.5 w-3.5 mr-1" />
          Nhập từ liên kết VBPL
        </button>
      </div>

      {mode === 'url' ? (
        <form onSubmit={handleUrlSubmit} className="space-y-3" noValidate>
          <div className="space-y-1.5">
            <Label htmlFor="legal-url-input">Đường dẫn văn bản vbpl.vn</Label>
            <Input
              id="legal-url-input"
              type="url"
              placeholder="https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=..."
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              disabled={isSubmitting}
            />
            <p className="text-xs text-muted-foreground">
              Hệ thống sẽ tự động bóc tách số hiệu, ngày ban hành, hiệu lực và tệp văn bản từ liên kết.
            </p>
          </div>
          {error && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
          )}
          <Button type="submit" disabled={isSubmitting} className="w-full">
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-1" /> Đang thu thập…
              </>
            ) : (
              <>
                <LinkIcon className="h-4 w-4 mr-1" /> Thu thập & Nạp văn bản
              </>
            )}
          </Button>
        </form>
      ) : (
        <form onSubmit={handleFileSubmit} className="space-y-3" noValidate>
      <div className="space-y-1.5">
        <Label htmlFor="legal-file">Tệp văn bản</Label>
        <Input
          id="legal-file"
          ref={fileInput}
          type="file"
          accept={ACCEPTED_FILES}
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="legal-number">Số hiệu</Label>
          <Input
            id="legal-number"
            placeholder="31/2024/QH15"
            value={values.number}
            onChange={(event) => update('number')(event.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="legal-doc-type">Loại văn bản</Label>
          <select
            id="legal-doc-type"
            value={values.doc_type}
            onChange={(event) => update('doc_type')(event.target.value)}
            className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm shadow-xs"
          >
            {Object.entries(DOC_TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="legal-title">Tên văn bản</Label>
        <Input id="legal-title" value={values.title} onChange={(event) => update('title')(event.target.value)} />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="legal-issuer">Cơ quan ban hành</Label>
        <Input id="legal-issuer" value={values.issuer} onChange={(event) => update('issuer')(event.target.value)} />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="legal-issued">Ngày ban hành</Label>
          <Input
            id="legal-issued"
            type="date"
            value={values.issued_date}
            onChange={(event) => update('issued_date')(event.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="legal-effective">Ngày hiệu lực</Label>
          <Input
            id="legal-effective"
            type="date"
            value={values.effective_date}
            onChange={(event) => update('effective_date')(event.target.value)}
          />
        </div>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="legal-source">Nguồn (URL)</Label>
        <Input
          id="legal-source"
          placeholder="https://vbpl.vn/..."
          value={values.source_url}
          onChange={(event) => update('source_url')(event.target.value)}
        />
      </div>
      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
      )}
      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
        Tải lên
      </Button>
    </form>
    )}
  </div>
  )
}

