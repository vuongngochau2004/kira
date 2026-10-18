'use client'

import { AlertTriangle, CheckCircle2, History } from 'lucide-react'
import { formatLegalDate, isInForceOn, todayIso, validityLabel } from '@/lib/legal/format'
import type { LegalCitationInfo } from '@/lib/legal/types'
import { cn } from '@/lib/utils'

interface LegalValidityBadgeProps {
  legal: Pick<LegalCitationInfo, 'valid_from' | 'valid_to' | 'amended_after'>
  today?: string
  className?: string
}

export function LegalValidityBadge({ legal, today = todayIso(), className }: LegalValidityBadgeProps) {
  const inForce = isInForceOn(legal.valid_from, legal.valid_to, today)
  return (
    <span className={cn('inline-flex flex-wrap items-center gap-1', className)}>
      <span
        data-testid="legal-validity"
        data-in-force={inForce ? 'true' : 'false'}
        title={inForce ? 'Đang có hiệu lực hôm nay' : 'Không còn hiệu lực hôm nay'}
        className={cn(
          'inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[10px] font-medium normal-case tracking-normal',
          inForce
            ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300'
            : 'border-zinc-200 bg-zinc-100 text-zinc-600 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400',
        )}
      >
        {inForce ? <CheckCircle2 className="h-3 w-3" /> : <History className="h-3 w-3" />}
        {validityLabel(legal.valid_from, legal.valid_to)}
      </span>
      {legal.amended_after && (
        <span
          data-testid="legal-amended"
          className="inline-flex items-center gap-1 rounded-md border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium normal-case tracking-normal text-amber-700 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300"
        >
          <AlertTriangle className="h-3 w-3" />
          Đã sửa đổi từ {formatLegalDate(legal.amended_after)}
        </span>
      )}
    </span>
  )
}
