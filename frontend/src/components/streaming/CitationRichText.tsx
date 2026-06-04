'use client'

import { memo, useState, useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'
import { CitationBadge, parseContentWithCitations } from './CitationBadge'

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
  const [visibleContent, setVisibleContent] = useState(content)
  const [cursorVisible, setCursorVisible] = useState(true)
  const prevContentRef = useRef(content)

  // Smooth cursor blink
  useEffect(() => {
    const interval = setInterval(() => {
      setCursorVisible((v) => !v)
    }, 530)
    return () => clearInterval(interval)
  }, [])

  // Update visible content when streaming
  useEffect(() => {
    if (content !== prevContentRef.current) {
      const timer = setTimeout(() => {
        setVisibleContent(content)
        prevContentRef.current = content
      }, 10)
      return () => clearTimeout(timer)
    }
  }, [content])

  return (
    <div className={cn(
      'whitespace-pre-wrap leading-relaxed text-foreground',
      'text-[15px] md:text-base'
    )}>
      {visibleContent}
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
    <div className="whitespace-pre-wrap leading-relaxed text-foreground text-[15px] md:text-base">
      {parts.map((part, index) => {
        if (typeof part === 'string') {
          return part
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
