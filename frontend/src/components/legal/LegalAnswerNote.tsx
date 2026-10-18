import { AlertTriangle, CalendarClock } from 'lucide-react'
import { appliedDateLabel } from '@/lib/legal/format'
import type { LegalAnswerInfo } from '@/lib/legal/types'
import { cn } from '@/lib/utils'

interface LegalAnswerNoteProps {
  info: LegalAnswerInfo
  className?: string
}

/** The date a legal answer applies to, plus any notices from the backend. */
export function LegalAnswerNote({ info, className }: LegalAnswerNoteProps) {
  return (
    <div className={cn('space-y-1 text-xs', className)}>
      <div className="inline-flex items-center gap-1.5 rounded-md border border-sky-200 bg-sky-50 px-2 py-1 font-medium text-sky-800 dark:border-sky-900 dark:bg-sky-950 dark:text-sky-200">
        <CalendarClock className="h-3.5 w-3.5" />
        <span>{appliedDateLabel(info)}</span>
      </div>
      {info.notices.map((notice) => (
        <div key={notice} className="flex items-start gap-1.5 text-amber-700 dark:text-amber-300">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>{notice}</span>
        </div>
      ))}
    </div>
  )
}
