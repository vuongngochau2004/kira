'use client'

import { useState } from 'react'
import { History } from 'lucide-react'
import { ROLE_LABELS } from '@/lib/legal/format'
import type { LegalCitationInfo } from '@/lib/legal/types'
import { LegalValidityBadge } from './LegalValidityBadge'
import { ProvisionHistoryDialog } from './ProvisionHistoryDialog'

interface LegalCitationMetaProps {
  legal: LegalCitationInfo
  today?: string
}

/** Role, validity and history link for one legal citation (stops clicks from toggling the card). */
export function LegalCitationMeta({ legal, today }: LegalCitationMetaProps) {
  const [open, setOpen] = useState(false)
  return (
    <div
      className="mt-2 flex flex-wrap items-center gap-1.5"
      onClick={(event) => event.stopPropagation()}
      onKeyDown={(event) => event.stopPropagation()}
    >
      <span className="rounded-md bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
        {ROLE_LABELS[legal.role] ?? legal.role}
      </span>
      <LegalValidityBadge legal={legal} today={today} />
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground hover:bg-muted hover:text-primary"
        aria-label="Xem lịch sử hiệu lực"
      >
        <History className="h-3 w-3" />
        Lịch sử
      </button>
      <ProvisionHistoryDialog provisionKey={legal.provision_key} open={open} onOpenChange={setOpen} />
    </div>
  )
}
