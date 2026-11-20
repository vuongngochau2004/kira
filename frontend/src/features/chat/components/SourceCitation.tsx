'use client'

/**
 * Source badge layout adapted from AnythingLLM's Citations component (MIT License).
 * Source: frontend/src/components/WorkspaceChat/ChatContainer/ChatHistory/Citation/index.jsx
 * Revision: 64b599fc92a9c2f4d60f2f9244d278acfff73204
 * Copyright (c) Mintplex Labs Inc. See frontend/third_party/anything-llm-LICENSE.
 */

import { FileText, Globe } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface SourceChunk {
  id: string
  chunk_id?: string
  content: string
  score: number
  document_id?: string
  chunk_index?: number
  title?: string
  type?: 'pdf' | 'docx' | 'web'
}

interface SourceCitationProps {
  sources: SourceChunk[]
  onClick: () => void
  className?: string
}

export function SourceCitation({ sources, onClick, className }: SourceCitationProps): React.JSX.Element | null {
  if (sources.length === 0) return null

  const documents = Array.from(
    new Map(sources.map((source) => [
      source.document_id || source.title || source.id,
      source,
    ])).values()
  )
  const visibleDocuments = documents.slice(0, 3)
  const remainingCount = documents.length - visibleDocuments.length

  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`Mở nguồn: ${documents.length} tài liệu, ${sources.length} trích dẫn`}
      className={cn(
        'inline-flex max-w-full items-center gap-2 rounded-full px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-primary',
        className
      )}
    >
      <span>{documents.length} nguồn</span>
      <span className="relative h-[22px] shrink-0" style={{ width: visibleDocuments.length * 15 + 7 }} aria-hidden="true">
        {visibleDocuments.map((source, index) => {
          const Icon = source.type === 'web' ? Globe : FileText
          return (
            <span
              key={source.document_id || source.title || source.id}
              className="absolute top-0 flex h-[22px] w-[22px] items-center justify-center rounded-full border-2 border-background bg-muted text-foreground"
              style={{ left: index * 15, zIndex: visibleDocuments.length - index }}
            >
              <Icon className="h-3 w-3" />
            </span>
          )
        })}
      </span>
      {remainingCount > 0 && <span>+{remainingCount}</span>}
    </button>
  )
}
