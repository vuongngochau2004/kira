'use client'

import { memo, useState } from 'react'
import { ChevronDown, CircleCheck, CircleX, LoaderCircle, TriangleAlert, Workflow } from 'lucide-react'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import {
  describePipelineStep,
  formatDuration,
  totalDurationMs,
  type PipelineStep,
  type PipelineStepTone,
} from '@/features/chat/streaming'
import { cn } from '@/lib/utils'

interface PipelineTraceProps {
  steps: PipelineStep[]
  isStreaming: boolean
  className?: string
}

const TONE_ICON: Record<PipelineStepTone, typeof CircleCheck> = {
  success: CircleCheck,
  warning: TriangleAlert,
  error: CircleX,
}

const TONE_CLASS: Record<PipelineStepTone, string> = {
  success: 'text-emerald-600 dark:text-emerald-400',
  warning: 'text-amber-600 dark:text-amber-400',
  error: 'text-destructive',
}

/**
 * Collapsible timeline of how an answer was produced: intent classification followed by each
 * LangGraph node (orchestrator → retrieval → generation → quality gate, with regeneration loops).
 * Open while the answer streams, collapsed afterwards unless the user toggles it.
 */
export const PipelineTrace = memo(({ steps, isStreaming, className }: PipelineTraceProps) => {
  // null = follow the streaming state; a boolean = the user's explicit choice
  const [userOpen, setUserOpen] = useState<boolean | null>(null)
  const open = userOpen ?? isStreaming
  const total = totalDurationMs(steps)
  const lastStep = steps.at(-1)
  const lastStepPending = lastStep ? describePipelineStep(lastStep).pending : false

  return (
    <Collapsible
      open={open}
      onOpenChange={setUserOpen}
      className={cn('mb-1 rounded-lg border border-border/70 bg-muted/30 text-xs', className)}
    >
      <CollapsibleTrigger className="flex w-full items-center gap-2 px-3 py-2 text-left text-muted-foreground transition-colors hover:text-foreground">
        <Workflow className="h-3.5 w-3.5 shrink-0" />
        <span className="font-medium">Quá trình xử lý (LangGraph)</span>
        <span className="truncate">
          · {steps.length} bước{total > 0 ? ` · ${formatDuration(total)}` : ''}
        </span>
        {isStreaming && <LoaderCircle className="h-3.5 w-3.5 shrink-0 animate-spin" />}
        <ChevronDown
          className={cn('ml-auto h-3.5 w-3.5 shrink-0 transition-transform', open && 'rotate-180')}
        />
      </CollapsibleTrigger>

      <CollapsibleContent>
        <ol className="space-y-1.5 border-t border-border/60 px-3 py-2" aria-label="Các bước xử lý">
          {steps.map((step, index) => {
            const view = describePipelineStep(step)
            const Icon = view.pending ? LoaderCircle : TONE_ICON[view.tone]
            return (
              <li key={`${step.stage}-${index}`} className="flex gap-2">
                <Icon className={cn(
                  'mt-0.5 h-3.5 w-3.5 shrink-0',
                  view.pending ? 'animate-spin text-muted-foreground' : TONE_CLASS[view.tone]
                )} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-2">
                    <span className="font-medium text-foreground">{view.label}</span>
                    {view.detail && (
                      <span className="truncate text-muted-foreground">{view.detail}</span>
                    )}
                    {view.durationMs !== null && (
                      <span className="ml-auto shrink-0 tabular-nums text-muted-foreground">
                        {formatDuration(view.durationMs)}
                      </span>
                    )}
                  </div>
                  {view.notes.length > 0 && (
                    <ul className="mt-0.5 space-y-0.5 text-muted-foreground">
                      {view.notes.map((note) => (
                        <li key={note} className="truncate" title={note}>
                          – {note}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </li>
            )
          })}
          {isStreaming && !lastStepPending && (
            <li className="flex items-center gap-2 text-muted-foreground">
              <LoaderCircle className="h-3.5 w-3.5 shrink-0 animate-spin" />
              <span>Đang xử lý bước tiếp theo…</span>
            </li>
          )}
        </ol>
      </CollapsibleContent>
    </Collapsible>
  )
})
PipelineTrace.displayName = 'PipelineTrace'
