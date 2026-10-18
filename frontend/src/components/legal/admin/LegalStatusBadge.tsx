import { CANDIDATE_STATUS_LABELS, DOCUMENT_STATUS_LABELS } from '@/lib/legal/format'
import type { CandidateStatus, LegalDocumentStatus } from '@/lib/legal/types'
import { cn } from '@/lib/utils'

const TONES = {
  neutral: 'bg-muted text-muted-foreground',
  info: 'bg-sky-50 text-sky-700 dark:bg-sky-950 dark:text-sky-300',
  warning: 'bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
  success: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
  danger: 'bg-destructive/10 text-destructive',
} as const

const DOCUMENT_TONES: Record<LegalDocumentStatus, keyof typeof TONES> = {
  uploaded: 'info',
  parsing: 'info',
  in_review: 'warning',
  publishing: 'info',
  published: 'success',
  failed: 'danger',
}

const CANDIDATE_TONES: Record<CandidateStatus, keyof typeof TONES> = {
  pending: 'warning',
  approved: 'success',
  rejected: 'neutral',
  unresolved_target: 'danger',
}

function Pill({ tone, children }: { tone: keyof typeof TONES; children: string }) {
  return (
    <span className={cn('inline-flex shrink-0 items-center rounded-md px-2 py-0.5 text-xs font-medium', TONES[tone])}>
      {children}
    </span>
  )
}

export function DocumentStatusBadge({ status }: { status: LegalDocumentStatus }) {
  return <Pill tone={DOCUMENT_TONES[status]}>{DOCUMENT_STATUS_LABELS[status]}</Pill>
}

export function CandidateStatusBadge({ status }: { status: CandidateStatus }) {
  return <Pill tone={CANDIDATE_TONES[status]}>{CANDIDATE_STATUS_LABELS[status]}</Pill>
}
