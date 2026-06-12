/**
 * Simplified Chunk Viewer Component
 * Displays only relevant text segments with improved highlighting
 * Focuses on readability and accuracy
 */

'use client'

import { memo, useMemo, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { useImprovedTextMatching } from '../hooks/use-improved-text-matching'
import { findLongestMatch } from '../hooks/use-text-matching'
import type { DocumentChunk, SourceChunk } from '../types/source-panel-types'

// ============================================
// Types
// ============================================

interface SimplifiedChunkViewerProps {
  chunks: DocumentChunk[]
  activeChunkId: string | null
  onChunkClick: (chunkId: string) => void
  documentChunks: SourceChunk[]
  maxSegments?: number
}

interface RelevantSegment {
  ragChunkId: string
  chunkId: string
  chunkIndex: number
  page: number
  segment: string
  match: any
  relevance: number
  snippet?: string
}

// ============================================
// Component
// ============================================

export const SimplifiedChunkViewer = memo<SimplifiedChunkViewerProps>(
  ({
    chunks,
    activeChunkId,
    onChunkClick,
    documentChunks,
    maxSegments = 10,
  }) => {
    const { findRelevantSegment } = useImprovedTextMatching()

    // Extract only relevant segments from chunks
    const relevantSegments = useMemo(() => {
      const segments: RelevantSegment[] = []

      // Get active snippet for matching
      const activeSnippet = documentChunks.find(c => c.id === activeChunkId)?.snippet

      chunks.forEach((chunk, idx) => {
        const page = chunk.metadata?.page_number || chunk.metadata?.page || 1

        if (activeSnippet && activeChunkId) {
          const result = findRelevantSegment(chunk.content, activeSnippet)
          segments.push({
            ragChunkId: activeChunkId,
            chunkId: chunk.id,
            chunkIndex: idx,
            page,
            segment: result.segment,
            match: result.match,
            relevance: result.relevance,
            snippet: activeSnippet,
          })
        }

        // Also include other RAG chunks if they have high relevance
        documentChunks.forEach((ragChunk) => {
          if (ragChunk.id !== activeChunkId) {
            const result = findRelevantSegment(chunk.content, ragChunk.snippet)
            if (result.relevance >= 0.6) {
              segments.push({
                ragChunkId: ragChunk.id,
                chunkId: chunk.id,
                chunkIndex: idx,
                page,
                segment: result.segment,
                match: result.match,
                relevance: result.relevance,
                snippet: ragChunk.snippet,
              })
            }
          }
        })
      })

      // Sort by relevance and limit
      return segments
        .sort((a, b) => b.relevance - a.relevance)
        .slice(0, maxSegments)
    }, [chunks, activeChunkId, documentChunks, findRelevantSegment, maxSegments])

    // Auto-scroll to active segment
    useEffect(() => {
      if (activeChunkId) {
        const timer = setTimeout(() => {
          const el = document.querySelector(`[data-segment-id="${activeChunkId}"]`)
          if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' })
          }
        }, 200)
        return () => clearTimeout(timer)
      }
    }, [activeChunkId])

    if (relevantSegments.length === 0) {
      return (
        <div className="text-center text-muted-foreground py-8">
          Không tìm thấy đoạn văn bản liên quan.
        </div>
      )
    }

    return (
      <div className="space-y-4">
        {relevantSegments.map((seg, idx) => {
          const isActive = seg.ragChunkId === activeChunkId

          return (
            <div
              key={`${seg.ragChunkId}-${seg.chunkId}-${idx}`}
              data-segment-id={seg.ragChunkId}
              onClick={() => onChunkClick(seg.ragChunkId)}
              className={cn(
                'p-4 rounded-lg border transition-all cursor-pointer',
                isActive
                  ? 'bg-primary/10 border-primary/30 shadow-sm'
                  : 'bg-muted/30 border-border/50 hover:bg-muted/50 hover:border-border'
              )}
            >
              {/* Segment Header */}
              <div className="flex items-center justify-between mb-2 text-xs">
                <span className={cn(
                  'font-mono',
                  isActive ? 'text-primary font-semibold' : 'text-muted-foreground'
                )}>
                  Trích đoạn #{idx + 1}
                </span>
                <div className="flex items-center gap-2">
                  {seg.relevance > 0 && (
                    <span className={cn(
                      'font-mono text-[10px] px-2 py-0.5 rounded-full',
                      seg.relevance >= 0.8
                        ? 'bg-green-500/10 text-green-600'
                        : seg.relevance >= 0.5
                        ? 'bg-yellow-500/10 text-yellow-600'
                        : 'bg-gray-500/10 text-gray-600'
                    )}>
                      {Math.round(seg.relevance * 100)}% liên quan
                    </span>
                  )}
                  <span className="font-mono text-muted-foreground">
                    Trang {seg.page}
                  </span>
                </div>
              </div>

              {/* Segment Content with Highlight */}
              <div className={cn(
                'text-sm leading-relaxed',
                isActive && 'font-semibold text-foreground'
              )}>
                {renderSegmentWithHighlight(seg.segment, seg.snippet, isActive)}
              </div>
            </div>
          )
        })}
      </div>
    )
  }
)

SimplifiedChunkViewer.displayName = 'SimplifiedChunkViewer'

// ============================================
// Rendering Helper
// ============================================

function renderSegmentWithHighlight(
  segment: string,
  snippet: string | undefined,
  isActive: boolean
): React.ReactNode {
  if (!snippet) {
    return <p className="text-foreground">{segment}</p>
  }

  const match = findLongestMatch(segment, snippet)
  if (match) {
    const { index, length } = match
    const before = segment.substring(0, index)
    const highlighted = segment.substring(index, index + length)
    const after = segment.substring(index + length)

    return (
      <p>
        {before}
        <strong className={cn(
          'font-bold px-1 rounded',
          isActive
            ? 'bg-primary/40 text-foreground ring-1 ring-primary/50'
            : 'bg-primary/25 text-foreground'
        )}>
          {highlighted}
        </strong>
        {after}
      </p>
    )
  }

  return <p className={isActive ? 'font-semibold' : ''}>{segment}</p>
}
