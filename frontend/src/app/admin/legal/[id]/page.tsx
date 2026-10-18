'use client'

import { useCallback, useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { RefreshCw } from 'lucide-react'
import { CandidateReviewCard } from '@/components/legal/admin/CandidateReviewCard'
import { LegalAdminShell } from '@/components/legal/admin/LegalAdminShell'
import { LegalDocumentActions } from '@/components/legal/admin/LegalDocumentActions'
import { DocumentStatusBadge } from '@/components/legal/admin/LegalStatusBadge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { legalAPI } from '@/lib/api/legal-client'
import { ACTIVE_DOCUMENT_STATUSES, DOC_TYPE_LABELS, formatLegalDate } from '@/lib/legal/format'
import type { CandidateReview, LegalDocument, RelationCandidate } from '@/lib/legal/types'

const WARNING_LABELS: Record<string, string> = {
  unbalanced_quotes: 'Văn bản có dấu ngoặc kép không cân đối (có thể do lỗi OCR).',
  duplicate_provision_key: 'Có điều/khoản bị đánh số trùng.',
  llm_extraction_incomplete: 'Trích xuất bằng LLM chưa hoàn tất; hãy kiểm tra các điều sửa đổi bằng tay.',
}

export default function LegalDocumentPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [document, setDocument] = useState<LegalDocument | null>(null)
  const [candidates, setCandidates] = useState<RelationCandidate[]>([])
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      const [doc, items] = await Promise.all([legalAPI.getDocument(id), legalAPI.listCandidates(id)])
      setDocument(doc)
      setCandidates(items)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không tải được văn bản')
    }
  }, [id])

  useEffect(() => {
    void load()
  }, [load])

  const isActive = document !== null && ACTIVE_DOCUMENT_STATUSES.includes(document.status)
  useEffect(() => {
    if (!isActive) return
    const timer = setInterval(() => void load(), 4000)
    return () => clearInterval(timer)
  }, [isActive, load])

  /** Run an action; it may return its own success message instead of the default one. */
  const run = async (action: () => Promise<string | void>, success: string) => {
    setBusy(true)
    setMessage(null)
    try {
      const actionMessage = await action()
      setMessage(actionMessage || success)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Thao tác thất bại')
    } finally {
      setBusy(false)
    }
  }

  const review = (candidate: RelationCandidate, decision: CandidateReview) =>
    run(async () => {
      const result = await legalAPI.review(candidate.id, decision)
      if (result.republish_task_id) {
        return 'Đã lưu. Văn bản đang được xuất bản lại để cập nhật đồ thị.'
      }
    }, 'Đã lưu quyết định duyệt.')

  const remove = () =>
    run(async () => {
      await legalAPI.remove(id)
      router.push('/admin/legal')
    }, 'Đã xóa văn bản.')

  const pending = candidates.filter((c) => c.status === 'pending' || c.status === 'unresolved_target').length

  return (
    <LegalAdminShell
      title={document ? document.number : 'Văn bản pháp luật'}
      description={document?.title ?? 'Chi tiết văn bản'}
      backHref="/admin/legal"
      actions={
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={busy}>
          <RefreshCw className="h-4 w-4" />
          Làm mới
        </Button>
      }
    >
      {error && (
        <div className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
      )}
      {message && (
        <div className="mb-4 rounded-lg border border-emerald-300/60 bg-emerald-50 p-3 text-sm text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">
          {message}
        </div>
      )}
      {document && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-center gap-2">
                <CardTitle>{document.title}</CardTitle>
                <DocumentStatusBadge status={document.status} />
              </div>
              <CardDescription>
                {DOC_TYPE_LABELS[document.doc_type]} số {document.number} · {document.issuer} · ban hành{' '}
                {formatLegalDate(document.issued_date)} · hiệu lực {formatLegalDate(document.effective_date)}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                {document.provision_count} điều khoản · {candidates.length} quan hệ đề xuất ({pending} chờ xử lý)
              </p>
              {document.error_detail && (
                <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                  {document.error_detail}
                </div>
              )}
              {document.warnings.map((warning) => (
                <div
                  key={warning}
                  className="rounded-lg border border-amber-300/60 bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-200"
                >
                  {WARNING_LABELS[warning] ?? warning}
                </div>
              ))}
              <LegalDocumentActions
                document={document}
                busy={busy}
                onPublish={() =>
                  void run(async () => {
                    await legalAPI.publish(id)
                  }, 'Đã gửi yêu cầu xuất bản.')
                }
                onReprocess={() =>
                  void run(async () => {
                    await legalAPI.reprocess(id)
                  }, 'Đã gửi yêu cầu phân tích lại.')
                }
                onDelete={() => void remove()}
              />
            </CardContent>
          </Card>

          <section className="space-y-3">
            <h2 className="text-sm font-semibold">Quan hệ đề xuất</h2>
            {candidates.length === 0 ? (
              <p className="text-sm text-muted-foreground">Chưa có quan hệ nào được đề xuất.</p>
            ) : (
              candidates.map((candidate) => (
                <CandidateReviewCard
                  key={candidate.id}
                  candidate={candidate}
                  busy={busy}
                  onReview={(decision) => void review(candidate, decision)}
                />
              ))
            )}
          </section>
        </div>
      )}
    </LegalAdminShell>
  )
}
