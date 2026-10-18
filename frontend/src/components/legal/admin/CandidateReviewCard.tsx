'use client'

import { useState } from 'react'
import { Check, Pencil, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { formatLegalDate, RELATION_TYPE_LABELS } from '@/lib/legal/format'
import type { CandidateReview, RelationCandidate } from '@/lib/legal/types'
import { CandidateStatusBadge } from './LegalStatusBadge'

interface CandidateReviewCardProps {
  candidate: RelationCandidate
  busy: boolean
  onReview: (review: CandidateReview) => void
}

export function CandidateReviewCard({ candidate, busy, onReview }: CandidateReviewCardProps) {
  const [note, setNote] = useState('')
  const [isEditing, setIsEditing] = useState(false)
  const [draft, setDraft] = useState({
    target_number: candidate.target_number,
    target_provision_ref: candidate.target_provision_ref ?? '',
    effective_date: candidate.effective_date,
    new_text: candidate.new_text ?? '',
  })

  const withNote = (review: CandidateReview): CandidateReview =>
    note.trim() ? { ...review, note: note.trim() } : review

  const saveEdit = () => {
    const review: CandidateReview = { action: 'edit' }
    if (draft.target_number !== candidate.target_number) review.target_number = draft.target_number
    if (draft.target_provision_ref !== (candidate.target_provision_ref ?? '')) {
      review.target_provision_ref = draft.target_provision_ref
    }
    if (draft.effective_date !== candidate.effective_date) review.effective_date = draft.effective_date
    if (draft.new_text !== (candidate.new_text ?? '')) review.new_text = draft.new_text
    onReview(withNote(review))
    setIsEditing(false)
  }

  const target = candidate.target_provision_ref
    ? `${candidate.target_number} · ${candidate.target_provision_ref}`
    : candidate.target_number
  const field = (key: keyof typeof draft) => (value: string) =>
    setDraft((current) => ({ ...current, [key]: value }))

  return (
    <article className="space-y-3 rounded-lg border p-4">
      <header className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold">{RELATION_TYPE_LABELS[candidate.type]}</span>
        <CandidateStatusBadge status={candidate.status} />
        <span className="text-xs text-muted-foreground">
          {candidate.extractor} · {(candidate.confidence * 100).toFixed(0)}%
        </span>
      </header>

      <div className="grid gap-3 md:grid-cols-2">
        <section className="space-y-1">
          <p className="text-xs font-medium uppercase text-muted-foreground">
            Bằng chứng{candidate.evidence_page ? ` · trang ${candidate.evidence_page}` : ''}
          </p>
          <blockquote className="whitespace-pre-line rounded-md border-l-4 border-l-orange-600 bg-muted/30 p-2 text-sm">
            {candidate.evidence_text}
          </blockquote>
          {candidate.source_provision_key && (
            <p className="font-mono text-xs text-muted-foreground">{candidate.source_provision_key}</p>
          )}
        </section>

        <section className="space-y-1">
          <p className="text-xs font-medium uppercase text-muted-foreground">Đề xuất</p>
          {isEditing ? (
            <div className="space-y-2">
              <div className="space-y-1">
                <Label htmlFor={`target-number-${candidate.id}`}>Số hiệu văn bản đích</Label>
                <Input
                  id={`target-number-${candidate.id}`}
                  value={draft.target_number}
                  onChange={(event) => field('target_number')(event.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor={`target-ref-${candidate.id}`}>Điều khoản đích</Label>
                <Input
                  id={`target-ref-${candidate.id}`}
                  placeholder="D12.K3.a"
                  value={draft.target_provision_ref}
                  onChange={(event) => field('target_provision_ref')(event.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor={`effective-${candidate.id}`}>Ngày hiệu lực</Label>
                <Input
                  id={`effective-${candidate.id}`}
                  type="date"
                  value={draft.effective_date}
                  onChange={(event) => field('effective_date')(event.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor={`new-text-${candidate.id}`}>Nội dung mới</Label>
                <Textarea
                  id={`new-text-${candidate.id}`}
                  rows={4}
                  value={draft.new_text}
                  onChange={(event) => field('new_text')(event.target.value)}
                />
              </div>
            </div>
          ) : (
            <div className="space-y-1 text-sm">
              <p className="font-mono">{target}</p>
              <p className="text-xs text-muted-foreground">Hiệu lực từ {formatLegalDate(candidate.effective_date)}</p>
              {candidate.new_text && (
                <p className="whitespace-pre-line rounded-md bg-muted/30 p-2">{candidate.new_text}</p>
              )}
            </div>
          )}
        </section>
      </div>

      {candidate.review_note && (
        <p className="text-xs text-muted-foreground">Ghi chú trước: {candidate.review_note}</p>
      )}

      <div className="space-y-1">
        <Label htmlFor={`note-${candidate.id}`}>Ghi chú duyệt</Label>
        <Input id={`note-${candidate.id}`} value={note} onChange={(event) => setNote(event.target.value)} />
      </div>

      <footer className="flex flex-wrap gap-2">
        {isEditing ? (
          <>
            <Button size="sm" onClick={saveEdit} disabled={busy}>
              Lưu thay đổi
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setIsEditing(false)} disabled={busy}>
              Hủy
            </Button>
          </>
        ) : (
          <>
            <Button
              size="sm"
              onClick={() => onReview(withNote({ action: 'approve' }))}
              disabled={busy || candidate.status === 'approved' || candidate.status === 'unresolved_target'}
            >
              <Check className="h-4 w-4" />
              Duyệt
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => onReview(withNote({ action: 'reject' }))}
              disabled={busy || candidate.status === 'rejected'}
            >
              <X className="h-4 w-4" />
              Từ chối
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setIsEditing(true)} disabled={busy}>
              <Pencil className="h-4 w-4" />
              Sửa
            </Button>
          </>
        )}
      </footer>
    </article>
  )
}
