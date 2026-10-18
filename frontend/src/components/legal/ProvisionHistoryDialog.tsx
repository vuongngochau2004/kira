'use client'

import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { legalAPI } from '@/lib/api/legal-client'
import { validityLabel } from '@/lib/legal/format'
import type { ProvisionHistory } from '@/lib/legal/types'
import { cn } from '@/lib/utils'

interface ProvisionHistoryDialogProps {
  provisionKey: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ProvisionHistoryDialog({ provisionKey, open, onOpenChange }: ProvisionHistoryDialogProps) {
  const [history, setHistory] = useState<ProvisionHistory | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!open || !provisionKey) return
    let cancelled = false
    setIsLoading(true)
    setError(null)
    legalAPI
      .provisionHistory(provisionKey)
      .then((result) => {
        if (!cancelled) setHistory(result)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Không tải được lịch sử điều khoản')
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [open, provisionKey])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {history ? `${history.label} — ${history.title} (${history.number})` : 'Lịch sử hiệu lực'}
          </DialogTitle>
          <DialogDescription>Các phiên bản của điều khoản theo thời gian.</DialogDescription>
        </DialogHeader>

        {isLoading && (
          <div className="flex justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        )}
        {error && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </div>
        )}
        {history && !isLoading && (
          <ol className="space-y-3">
            {history.versions.map((version) => {
              const current = history.in_force?.version_id === version.version_id
              return (
                <li
                  key={version.version_id}
                  className={cn(
                    'rounded-lg border p-3',
                    current ? 'border-emerald-300 bg-emerald-50/60 dark:border-emerald-800 dark:bg-emerald-950/40' : 'border-border',
                  )}
                >
                  <div className="mb-2 flex items-center justify-between gap-2 text-xs text-muted-foreground">
                    <span>{validityLabel(version.valid_from, version.valid_to)}</span>
                    {current && (
                      <span className="rounded-md bg-emerald-600 px-1.5 py-0.5 text-[10px] font-medium text-white">
                        Đang áp dụng
                      </span>
                    )}
                  </div>
                  <p className="whitespace-pre-line text-sm leading-6">{version.text}</p>
                </li>
              )
            })}
          </ol>
        )}
      </DialogContent>
    </Dialog>
  )
}
