/**
 * Chunk Renderer Component
 * Renders document chunks with highlighting for active selections
 */

import { memo, useMemo, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { cleanStringForMatching, findLongestMatch, groupChunksByPage } from '../hooks/use-text-matching'
import type { DocumentChunk, SourceChunk } from '../types/source-panel-types'

interface ChunkRendererProps {
  chunks: DocumentChunk[]
  activeChunkId: string | null
  onChunkClick: (chunkId: string) => void
  documentChunks: SourceChunk[]
}

export const ChunkRenderer = memo<ChunkRendererProps>(
  ({ chunks, activeChunkId, onChunkClick, documentChunks }) => {
    // Keep page grouping for order, but do not render separate page labels.
    const chunksByPage = useMemo(() => groupChunksByPage(chunks), [chunks])

    // Auto-scroll to active chunk
    useEffect(() => {
      if (activeChunkId) {
        const timer = setTimeout(() => {
          const el = document.getElementById(`preview-chunk-${activeChunkId}`)
          if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' })
          }
        }, 200)
        return () => clearTimeout(timer)
      }
    }, [activeChunkId])

    // Find the active chunk's snippet for highlighting
    const activeSnippet = useMemo(() => {
      if (!activeChunkId) return null
      const activeDocChunk = documentChunks.find((c) => c.id === activeChunkId)
      return activeDocChunk?.snippet || null
    }, [activeChunkId, documentChunks])

    const handleChunkClick = (chunk: DocumentChunk) => {
      // Find matching RAG chunk
      const matchedRagChunk = documentChunks.find((ragChunk) => {
        const cleanedS = cleanStringForMatching(ragChunk.snippet)
        const cleanedC = cleanStringForMatching(chunk.content)
        return (
          cleanedS &&
          cleanedC &&
          (cleanedC.includes(cleanedS) || cleanedS.includes(cleanedC))
        )
      })

      if (matchedRagChunk) {
        onChunkClick(matchedRagChunk.id)
      } else {
        onChunkClick(chunk.id)
      }
    }

    return (
      <div className="space-y-6">
        {Object.entries(chunksByPage).map(([pageNum, pageChunks]) => (
          <div key={pageNum} className="space-y-2">
            <p className="indent-6 text-justify leading-relaxed">
              {pageChunks.map((chunk, idx) => {
                const isSelected = activeChunkId === chunk.id
                const isActiveSnippet = activeSnippet ? [activeSnippet] : []

                return (
                  <span
                    key={chunk.id}
                    id={`preview-chunk-${chunk.id}`}
                    onClick={() => handleChunkClick(chunk)}
                    className={cn(
                      'transition-all cursor-pointer px-0.5 rounded',
                      isSelected && 'ring-1 ring-primary/30'
                    )}
                  >
                    {renderHighlightedText(chunk.content, isActiveSnippet, isSelected)}{' '}
                  </span>
                )
              })}
            </p>
          </div>
        ))}
      </div>
    )
  }
)

ChunkRenderer.displayName = 'ChunkRenderer'

// ============================================
// Text Highlighting Component
// ============================================

interface HighlightedTextProps {
  content: string
  snippets: string[]
  isSelected: boolean
}

function renderHighlightedText(content: string, snippets: string[], isSelected: boolean) {
  if (!snippets || snippets.length === 0) {
    return (
      <span
        className={isSelected
          ? 'font-bold bg-primary/30 px-0.5 rounded text-foreground'
          : ''
        }
      >
        {content}
      </span>
    )
  }

  // Find the best matching snippet
  let bestMatch: { index: number; length: number } | null = null

  for (const snippet of snippets) {
    const match = findLongestMatch(content, snippet)
    if (match) {
      if (!bestMatch || match.length > bestMatch.length) {
        bestMatch = match
      }
    }
  }

  if (bestMatch) {
    const { index, length } = bestMatch
    const before = content.substring(0, index)
    const match = content.substring(index, index + length)
    const after = content.substring(index + length)

    return (
      <span>
        {before}
        <strong
          className={cn(
            'font-bold text-foreground px-0.5 rounded',
            isSelected
              ? 'bg-primary/45 ring-1 ring-primary/60'
              : 'bg-primary/25'
          )}
        >
          {match}
        </strong>
        {after}
      </span>
    )
  }

  // No match found, render as normal
  return (
    <span
      className={isSelected
        ? 'font-bold bg-primary/35 px-0.5 rounded ring-1 ring-primary/40 text-foreground'
        : ''
      }
    >
      {content}
    </span>
  )
}
