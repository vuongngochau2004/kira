'use client'

import { memo, useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn } from '@/lib/utils'
import { parseContentWithCitations } from './CitationBadge'

export interface CitationSource {
  chunk_id: string
  source: string
  title?: string
  snippet?: string
  content: string
  content_length?: number
  page_number?: number
  score?: number
  grounding_score?: number
  document_id?: string
  chunk_index?: number
}

export interface VerificationStats {
  verified: number
  hallucinated: number
  weak_grounding: number
  missing: number
  total: number
}

interface CitationRichTextProps {
  content: string
  citations?: CitationSource[]
  isStreaming?: boolean
  className?: string
  onCitationClick?: (chunkId: string, citation: CitationSource) => void
}

/**
 * Streaming content with cursor animation
 */
const StreamingContent = memo(({ content }: { content: string }) => {
  const [cursorVisible, setCursorVisible] = useState(true)

  // Smooth cursor blink
  useEffect(() => {
    const interval = setInterval(() => {
      setCursorVisible((v) => !v)
    }, 530)
    return () => clearInterval(interval)
  }, [])

  // Clean up inline [source:...] citations along with any leading spaces as requested by user
  const cleanedContent = content.replace(/\s*\[source:[^\]]*\]/g, '')

  return (
    <div className={cn(
      'whitespace-pre-wrap leading-relaxed text-foreground',
      'text-[15px] md:text-base'
    )}>
      {cleanedContent}
      <span
        className={cn(
          'inline-block w-0.5 h-4 bg-primary ml-0.5 align-middle',
          'transition-opacity duration-200',
          cursorVisible ? 'opacity-100' : 'opacity-0'
        )}
      />
    </div>
  )
})
StreamingContent.displayName = 'StreamingContent'

/**
 * Static content with inline citation badges
 */
const StaticContent = memo(({
  content,
  citations = [],
  onCitationClick
}: {
  content: string
  citations?: CitationSource[]
  onCitationClick?: (chunkId: string, citation: CitationSource) => void
}) => {
  const parts = parseContentWithCitations(content, citations, onCitationClick)

  return (
    <div className="leading-relaxed text-[15px] md:text-base">
      {parts.map((part, index) => {
        if (typeof part === 'string') {
          return (
            <ReactMarkdown
              key={index}
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => <p className="mb-4 last:mb-0 leading-relaxed text-foreground">{children}</p>,
                strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
                ul: ({ children }) => <ul className="list-disc pl-5 mb-4 space-y-1 text-foreground">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal pl-5 mb-4 space-y-1 text-foreground">{children}</ol>,
                li: ({ children }) => <li className="leading-relaxed text-foreground">{children}</li>,
                h1: ({ children }) => <h1 className="text-2xl font-bold mt-6 mb-3 text-foreground">{children}</h1>,
                h2: ({ children }) => <h2 className="text-xl font-bold mt-5 mb-2.5 text-foreground">{children}</h2>,
                h3: ({ children }) => <h3 className="text-lg font-semibold mt-4 mb-2 text-foreground">{children}</h3>,
                code: ({ className, children }) => {
                  const match = /language-(\w+)/.exec(className || '')
                  return match ? (
                    <pre className="bg-muted p-4 rounded-xl overflow-x-auto text-sm my-4 font-mono text-foreground">
                      <code>{children}</code>
                    </pre>
                  ) : (
                    <code className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono text-foreground">{children}</code>
                  )
                }
              }}
            >
              {part}
            </ReactMarkdown>
          )
        }
        return <span key={index}>{part}</span>
      })}
    </div>
  )
})
StaticContent.displayName = 'StaticContent'

/**
 * CitationRichText component for displaying content with [source:chunk_id] citations.
 *
 * Handles:
 * - Streaming mode with cursor animation
 * - Static mode with clickable citation badges
 * - Auto-parsing of [source:chunk_id] markers
 */
export function CitationRichText({
  content,
  citations = [],
  isStreaming = false,
  className,
  onCitationClick
}: CitationRichTextProps) {
  return (
    <div className={cn('prose dark:prose-invert max-w-none', className)}>
      {isStreaming ? (
        <StreamingContent content={content} />
      ) : (
        <StaticContent
          content={content}
          citations={citations}
          onCitationClick={onCitationClick}
        />
      )}
    </div>
  )
}
