'use client'

import { useState, useRef, useEffect } from 'react'
import { X, Search, FileText, Loader2, CheckCircle, AlertTriangle, XCircle, Info } from 'lucide-react'
import { cn } from '@/lib/utils'
import { CitationBadge } from './CitationBadge'

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
  verified?: boolean
}

export interface VerificationStats {
  verified: number
  hallucinated: number
  weak_grounding: number
  missing: number
  total: number
}

interface CitationPanelProps {
  citations: CitationSource[]
  isOpen: boolean
  onClose: () => void
  verificationStats?: VerificationStats
  activeChunkId?: string | null
  className?: string
}

/**
 * CitationPanel - Sidebar panel displaying source details with verification status.
 *
 * Shows:
 * - Verification statistics summary
 * - Full source list with titles, page numbers, snippets
 * - Verification status indicators
 * - Confidence scores
 */
export function CitationPanel({
  citations,
  isOpen,
  onClose,
  verificationStats,
  activeChunkId,
  className
}: CitationPanelProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())
  const [loadingIds, setLoadingIds] = useState<Set<string>>(new Set())
  const activeRef = useRef<HTMLDivElement>(null)

  // Auto-expand active source and scroll into view
  useEffect(() => {
    if (isOpen && activeChunkId) {
      setExpandedIds((prev) => {
        const next = new Set(prev)
        if (!next.has(activeChunkId)) {
          next.add(activeChunkId)
          setLoadingIds((load) => new Set(load).add(activeChunkId))
          setTimeout(() => {
            setLoadingIds((load) => {
              const nextLoad = new Set(load)
              nextLoad.delete(activeChunkId)
              return nextLoad
            })
          }, 300)
        }
        return next
      })
      setTimeout(() => {
        activeRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }, 400)
    }
  }, [isOpen, activeChunkId])

  if (!isOpen) return null

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
        setLoadingIds((load) => new Set(load).add(id))
        setTimeout(() => {
          setLoadingIds((load) => {
            const nextLoad = new Set(load)
            nextLoad.delete(id)
            return nextLoad
          })
        }, 300)
      }
      return next
    })
  }

  const getStatusColor = (citation: CitationSource) => {
    if (citation.grounding_score !== undefined) {
      if (citation.grounding_score >= 0.7) return 'text-green-600 dark:text-green-400'
      if (citation.grounding_score >= 0.4) return 'text-yellow-600 dark:text-yellow-400'
      return 'text-red-600 dark:text-red-400'
    }
    return 'text-gray-400'
  }

  const getStatusIcon = (citation: CitationSource) => {
    if (citation.grounding_score !== undefined) {
      if (citation.grounding_score >= 0.7) return <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
      if (citation.grounding_score >= 0.4) return <AlertTriangle className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />
      return <XCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
    }
    return <Info className="w-4 h-4 text-gray-400" />
  }

  return (
    <div className={cn(
      'fixed right-0 top-0 h-full w-96 border-l bg-background shadow-lg z-50 transition-transform',
      'flex flex-col',
      isOpen ? 'translate-x-0' : 'translate-x-full',
      className
    )}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <div className="flex items-center gap-2">
          <Search className="w-4 h-4 text-muted-foreground" />
          <h3 className="font-semibold">Nguồn trích dẫn</h3>
          <span className="text-muted-foreground text-xs">({citations.length})</span>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-muted rounded-md transition-colors"
          title="Đóng"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Verification Stats */}
      {verificationStats && (
        <div className="px-4 py-3 border-b bg-muted/30">
          <div className="text-xs font-medium text-muted-foreground mb-2">
            Tình trạng kiểm chứng:
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="flex items-center gap-1.5">
              <CheckCircle className="w-3.5 h-3.5 text-green-600 dark:text-green-400" />
              <span>Chính xác: {verificationStats.verified}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-yellow-600 dark:text-yellow-400" />
              <span>Yếu: {verificationStats.weak_grounding}</span>
            </div>
            {verificationStats.hallucinated > 0 && (
              <div className="flex items-center gap-1.5 text-red-600 dark:text-red-400">
                <XCircle className="w-3.5 h-3.5" />
                <span>Sai: {verificationStats.hallucinated}</span>
              </div>
            )}
            {verificationStats.missing > 0 && (
              <div className="flex items-center gap-1.5 text-gray-500">
                <Info className="w-3.5 h-3.5" />
                <span>Thiếu: {verificationStats.missing}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto divide-y">
        {citations.map((citation, index) => {
          const sourceKey = citation.chunk_id || `source-${index}`
          const isExpanded = expandedIds.has(sourceKey)
          const isLoading = loadingIds.has(sourceKey)
          const isActive = sourceKey === activeChunkId

          return (
            <div
              key={sourceKey}
              ref={isActive ? activeRef : null}
              className={cn(
                "p-3 transition-all",
                isActive && "bg-primary/5 border-l-2 border-primary"
              )}
            >
              <button
                onClick={() => toggleExpand(sourceKey)}
                className="flex items-start gap-2 w-full text-left hover:bg-muted/50 rounded-md p-2 -m-2 transition-colors"
              >
                <FileText className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-sm">
                      {citation.title || citation.source}
                    </span>
                    {isActive && (
                      <span className={cn(
                        'inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded-full',
                        'bg-primary/20 text-primary font-medium'
                      )}>
                        <Info className="w-3 h-3" />
                        Đang xem
                      </span>
                    )}
                    {getStatusIcon(citation)}
                  </div>

                  <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                    {citation.page_number !== undefined && (
                      <span>Trang {citation.page_number}</span>
                    )}
                    {citation.chunk_index !== undefined && (
                      <span>• Chunk #{citation.chunk_index}</span>
                    )}
                    {citation.score !== undefined && (
                      <span>• Relevance: {(citation.score * 100).toFixed(0)}%</span>
                    )}
                  </div>

                  {!isExpanded && citation.snippet && (
                    <p className="text-muted-foreground text-xs line-clamp-2 mt-2">
                      {citation.snippet}
                      {citation.content_length && citation.content_length > citation.snippet.length && '...'}
                    </p>
                  )}
                </div>
              </button>

              {isExpanded && (
                <div className={cn(
                  "ml-6 mt-2 text-sm text-foreground p-3 rounded-lg",
                  isActive && "bg-primary/10 border border-primary/20"
                )}>
                  {isLoading ? (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      <span>Đang tải...</span>
                    </div>
                  ) : (
                    <>
                      <p className="whitespace-pre-wrap leading-relaxed">
                        {citation.content}
                      </p>
                      {isActive && (
                        <div className="mt-3 pt-3 border-t border-primary/20">
                          <p className="text-xs text-muted-foreground italic">
                            ✦ Đây là nội dung được tham chiếu từ câu trả lời
                          </p>
                        </div>
                      )}
                      {citation.grounding_score !== undefined && (
                        <div className="mt-3 pt-3 border-t">
                          <div className="flex items-center gap-2 text-xs">
                            <span className="text-muted-foreground">Độ tin cậy:</span>
                            <span className={cn(
                              'font-medium',
                              getStatusColor(citation)
                            )}>
                              {(citation.grounding_score * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          )
        })}

        {citations.length === 0 && (
          <div className="p-8 text-center text-muted-foreground">
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">Không có nguồn trích dẫn</p>
          </div>
        )}
      </div>
    </div>
  )
}
