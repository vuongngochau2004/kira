"use client"

/**
 * Adapted from AnythingLLM's SourceItem component (MIT License).
 * Source: frontend/src/components/WorkspaceChat/ChatContainer/SourcesSidebar/SourceItem/index.jsx
 * Revision: 64b599fc92a9c2f4d60f2f9244d278acfff73204
 * Copyright (c) Mintplex Labs Inc. See frontend/third_party/anything-llm-LICENSE.
 */

import { ChevronDown, FileText, Globe } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { SupportedFileType } from '@/features/chat/sources/types'

interface SourceSummaryProps {
  title: string
  type: SupportedFileType
  referenceCount: number
  expanded: boolean
  onExpand: () => void
}

export function SourceSummary({
  title,
  type,
  referenceCount,
  expanded,
  onExpand,
}: SourceSummaryProps): React.JSX.Element {
  const Icon = type === 'web' ? Globe : FileText

  return (
    <button
      type="button"
      onClick={onExpand}
      aria-expanded={expanded}
      aria-label={`${expanded ? 'Thu gọn' : 'Mở'} ${title}, ${referenceCount} trích dẫn`}
      className="flex w-full min-w-0 items-start gap-2.5 rounded-lg text-left focus-visible:outline-2 focus-visible:outline-primary"
    >
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border bg-muted text-muted-foreground" aria-hidden="true">
        <Icon className="h-3.5 w-3.5" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium leading-5 text-foreground" title={title}>{title}</span>
        <span className="block text-xs leading-5 text-muted-foreground">
          {type === 'web' ? 'Trang web' : 'Tài liệu'} · {referenceCount} trích dẫn
        </span>
      </span>
      <ChevronDown className={cn('mt-1 h-4 w-4 shrink-0 text-muted-foreground transition-transform', expanded && 'rotate-180')} aria-hidden="true" />
    </button>
  )
}
