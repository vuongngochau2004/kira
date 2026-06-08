'use client'

import { useState, useRef, useEffect, useMemo } from 'react'
import { X, Search, FileText, Loader2, CheckCircle, AlertTriangle, XCircle, Info, Eye } from 'lucide-react'
import { cn } from '@/lib/utils'
import { CitationBadge } from './CitationBadge'
import { documentsAPI } from '@/lib/api/simple-client'
import { DocumentPreviewDialog } from '@/components/document-preview-dialog'

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
  onActiveChunkIdChange?: (chunkId: string | null) => void
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
  onActiveChunkIdChange,
  className
}: CitationPanelProps) {
  const [expandedDocKeys, setExpandedDocKeys] = useState<Set<string>>(new Set())
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())
  const [loadingIds, setLoadingIds] = useState<Set<string>>(new Set())
  const activeRef = useRef<HTMLDivElement>(null)

  const [width, setWidth] = useState(384) // Default width of 384px (w-96 equivalent)
  const [isDragging, setIsDragging] = useState(false)
  const resizeRef = useRef<HTMLDivElement>(null)

  const [docChunks, setDocChunks] = useState<Record<string, Array<{ id: string; chunk_index: number; content: string; metadata?: any }>>>({})
  const [fetchingChunks, setFetchingChunks] = useState<Record<string, boolean>>({})
  const [expandedViewMode, setExpandedViewMode] = useState<Record<string, 'snippet' | 'context'>>({})
  const [previewDocId, setPreviewDocId] = useState<string | null>(null)
  const [previewFilename, setPreviewFilename] = useState<string>('')

  // Handle Drag-to-Resize Mouse Events
  useEffect(() => {
    if (!isOpen) return

    const handleMouseDown = (e: MouseEvent) => {
      e.preventDefault()
      setIsDragging(true)
    }

    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return
      const newWidth = window.innerWidth - e.clientX
      // Set constraints: min 320px, max 80% of window width
      if (newWidth >= 320 && newWidth <= window.innerWidth * 0.8) {
        setWidth(newWidth)
      }
    }

    const handleMouseUp = () => {
      setIsDragging(false)
    }

    const resizeEl = resizeRef.current
    if (resizeEl) {
      resizeEl.addEventListener('mousedown', handleMouseDown)
    }

    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove)
      window.addEventListener('mouseup', handleMouseUp)
    }

    return () => {
      if (resizeEl) {
        resizeEl.removeEventListener('mousedown', handleMouseDown)
      }
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging, isOpen])

  // Prevent text selection and change cursor on body during dragging
  useEffect(() => {
    if (isDragging) {
      document.body.style.cursor = 'ew-resize'
      document.body.style.userSelect = 'none'
    } else {
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
    return () => {
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isDragging])

  // Group citations by document title/id
  const groupedCitations = useMemo(() => {
    const groups: Record<string, {
      document_id: string | null
      title: string
      source: string
      maxScore: number
      citations: CitationSource[]
    }> = {}
    
    citations.forEach((citation) => {
      const key = citation.document_id || citation.title || citation.source || 'unknown'
      if (!groups[key]) {
        groups[key] = {
          document_id: citation.document_id || null,
          title: citation.title || citation.source || 'Tài liệu',
          source: citation.source || 'Tài liệu',
          maxScore: citation.score || 0,
          citations: []
        }
      }
      groups[key].citations.push(citation)
      if (citation.score !== undefined && citation.score > groups[key].maxScore) {
        groups[key].maxScore = citation.score
      }
    })
    
    return Object.values(groups)
  }, [citations])

  const loadDocChunks = (docId: string) => {
    if (docChunks[docId] !== undefined || fetchingChunks[docId]) return
    
    setFetchingChunks(prev => ({ ...prev, [docId]: true }))
    documentsAPI.getChunks(docId)
      .then(chunks => {
        setDocChunks(prev => ({ ...prev, [docId]: chunks }))
      })
      .catch(err => {
        console.error('Failed to load document chunks for CitationPanel:', err)
        setDocChunks(prev => ({ ...prev, [docId]: [] }))
      })
      .finally(() => {
        setFetchingChunks(prev => ({ ...prev, [docId]: false }))
      })
  }

  // Auto-expand active source and scroll into view
  useEffect(() => {
    if (isOpen && activeChunkId) {
      const activeCitation = citations.find(c => c.chunk_id === activeChunkId)
      if (activeCitation) {
        const docKey = activeCitation.document_id || activeCitation.title || activeCitation.source || 'unknown'
        setExpandedDocKeys((prev) => {
          const next = new Set(prev)
          next.add(docKey)
          return next
        })
      }
      setExpandedIds((prev) => {
        if (!prev.has(activeChunkId)) {
          setLoadingIds((load) => new Set(load).add(activeChunkId))
          setTimeout(() => {
            setLoadingIds((load) => {
              const nextLoad = new Set(load)
              nextLoad.delete(activeChunkId)
              return nextLoad
            })
          }, 300)
        }
        // Collapse all other expanded citations and only keep the active one
        return new Set([activeChunkId])
      })
      setTimeout(() => {
        activeRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }, 400)
    }
  }, [isOpen, activeChunkId, citations])

  if (!isOpen) return null

  const toggleExpand = (id: string) => {
    const isAlreadyExpanded = expandedIds.has(id)

    if (!isAlreadyExpanded) {
      setExpandedIds(new Set([id]))
      setLoadingIds((load) => {
        const next = new Set(load)
        next.add(id)
        return next
      })
      setTimeout(() => {
        setLoadingIds((load) => {
          const nextLoad = new Set(load)
          nextLoad.delete(id)
          return nextLoad
        })
      }, 300)
      // Set this citation as the active one in the parent component (outside state updater)
      onActiveChunkIdChange?.(id)
    } else {
      setExpandedIds(new Set())
      // Clear active selection when collapsed (outside state updater)
      onActiveChunkIdChange?.(null)
    }
  }

  const toggleDocExpand = (docKey: string) => {
    setExpandedDocKeys((prev) => {
      const next = new Set(prev)
      if (next.has(docKey)) {
        next.delete(docKey)
      } else {
        next.add(docKey)
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
    <div
      style={{
        width: isOpen ? `${width}px` : '0px',
        transition: isDragging ? 'none' : 'transform 0.3s ease-in-out, width 0.3s ease-in-out',
        maxWidth: '95vw'
      }}
      className={cn(
        'h-full bg-background z-50 flex flex-col overflow-hidden',
        isOpen && 'border-l border-border',
        // Mobile: fixed overlay
        'fixed right-0 top-0 shadow-lg lg:shadow-none lg:relative lg:right-auto lg:top-auto',
        // Open/Close sliding effect on mobile
        isOpen ? 'translate-x-0' : 'translate-x-full lg:translate-x-0',
        className
      )}
    >
      {/* Drag Resize Handle */}
      {isOpen && (
        <div
          ref={resizeRef}
          className={cn(
            "absolute left-0 top-0 w-2 h-full -translate-x-1/2 cursor-ew-resize select-none z-50",
            "group/resize transition-colors duration-150"
          )}
          onDoubleClick={() => setWidth(384)}
          title="Kéo để thay đổi kích thước, nhấn đúp để khôi phục mặc định"
        >
          <div className={cn(
            "w-[2px] h-full mx-auto transition-colors duration-150",
            "bg-border group-hover/resize:bg-primary group-active/resize:bg-primary/75",
            isDragging && "bg-primary"
          )} />
        </div>
      )}
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b shrink-0 bg-background">
        <div className="flex items-center gap-2">
          <Search className="w-4 h-4 text-muted-foreground" />
          <h3 className="font-semibold text-sm">Nguồn trích dẫn</h3>
          <span className="text-muted-foreground text-xs font-medium">({groupedCitations.length} file, {citations.length} trích dẫn)</span>
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
      <div className="flex-1 overflow-y-auto divide-y bg-muted/5">
        {groupedCitations.map((group, groupIndex) => {
          const docKey = group.document_id || group.title || group.source || 'unknown'
          const isDocExpanded = expandedDocKeys.has(docKey)
          const hasActiveChunkInDoc = activeChunkId && group.citations.some(c => c.chunk_id === activeChunkId)

          return (
            <div
              key={docKey}
              className={cn(
                "transition-all border-b last:border-b-0 bg-background",
                hasActiveChunkInDoc && "bg-primary/5"
              )}
            >
              {/* Document Header Card */}
              <button
                onClick={() => toggleDocExpand(docKey)}
                className={cn(
                  "flex items-start gap-3 w-full text-left p-4 hover:bg-muted/30 transition-colors select-none",
                  isDocExpanded && "border-b border-border/40"
                )}
              >
                <div className="shrink-0 w-8 h-8 rounded-xl bg-primary/10 flex items-center justify-center text-primary">
                  <FileText className="w-4.5 h-4.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold text-sm leading-tight text-foreground pr-2">
                    {group.title}
                  </h4>
                  <div className="flex items-center gap-2 mt-1.5 text-xs text-muted-foreground">
                    <span className="bg-primary/10 text-primary px-2 py-0.5 rounded-full font-medium text-[10px]">
                      {group.citations.length} trích dẫn
                    </span>
                    {group.maxScore > 0 && (
                      <span>• Trùng khớp: {(group.maxScore * 100).toFixed(0)}%</span>
                    )}
                  </div>
                </div>
              </button>

              {/* Citations list under document */}
              {isDocExpanded && (
                <div className="divide-y divide-border/30 bg-muted/10">
                  {group.citations.map((citation, index) => {
                    const sourceKey = citation.chunk_id || `source-${index}`
                    const isExpanded = expandedIds.has(sourceKey)
                    const isLoading = loadingIds.has(sourceKey)
                    const isActive = sourceKey === activeChunkId

                    return (
                      <div
                        key={sourceKey}
                        ref={isActive ? activeRef : null}
                        className={cn(
                          "pl-8 pr-4 py-3 transition-all",
                          isActive && "bg-primary/10 border-l-4 border-primary"
                        )}
                      >
                        <button
                          onClick={() => toggleExpand(sourceKey)}
                          className="flex items-start gap-2 w-full text-left hover:bg-muted/50 rounded-md p-1.5 -m-1.5 transition-colors"
                        >
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-medium text-xs text-foreground bg-muted px-2 py-0.5 rounded-md">
                                Trích dẫn #{index + 1}
                              </span>
                              {citation.page_number !== undefined && (
                                <span className="text-xs text-muted-foreground font-medium">
                                  Trang {citation.page_number}
                                </span>
                              )}
                              {isActive && (
                                <span className={cn(
                                  'inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full',
                                  'bg-primary text-primary-foreground font-semibold'
                                )}>
                                  Đang xem
                                </span>
                              )}
                              <div className="ml-auto flex items-center gap-1.5 shrink-0">
                                {getStatusIcon(citation)}
                              </div>
                            </div>

                            {!isExpanded && citation.snippet && (
                              <p className="text-muted-foreground text-xs line-clamp-2 mt-2 font-sans">
                                {citation.snippet}
                                {citation.content_length && citation.content_length > citation.snippet.length && '...'}
                              </p>
                            )}
                          </div>
                        </button>

                        {isExpanded && (
                          <div className={cn(
                            "mt-3 text-sm text-foreground p-3 rounded-lg bg-background border border-border/60",
                            isActive && "ring-1 ring-primary/20"
                          )}>
                            {isLoading ? (
                              <div className="flex items-center gap-2 text-muted-foreground">
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                <span>Đang tải...</span>
                              </div>
                            ) : (
                              <>
                                {citation.document_id && (
                                  <div className="flex gap-1 bg-muted p-0.5 rounded-lg text-xs w-fit mb-3">
                                    <button
                                      onClick={() => setExpandedViewMode(prev => ({ ...prev, [sourceKey]: 'snippet' }))}
                                      className={cn(
                                        "px-2.5 py-1 rounded-md transition-all font-medium",
                                        (expandedViewMode[sourceKey] || 'snippet') === 'snippet'
                                          ? "bg-background text-foreground shadow-sm"
                                          : "text-muted-foreground hover:text-foreground"
                                      )}
                                    >
                                      Trích dẫn
                                    </button>
                                    <button
                                      onClick={() => {
                                        setExpandedViewMode(prev => ({ ...prev, [sourceKey]: 'context' }))
                                        loadDocChunks(citation.document_id!)
                                      }}
                                      className={cn(
                                        "px-2.5 py-1 rounded-md transition-all font-medium",
                                        expandedViewMode[sourceKey] === 'context'
                                          ? "bg-background text-foreground shadow-sm"
                                          : "text-muted-foreground hover:text-foreground"
                                      )}
                                    >
                                      Xem ngữ cảnh
                                    </button>
                                  </div>
                                )}

                                {(expandedViewMode[sourceKey] || 'snippet') === 'snippet' ? (
                                  <p className="whitespace-pre-wrap leading-relaxed text-xs text-foreground/90 font-serif">
                                    {citation.content}
                                  </p>
                                ) : (
                                  /* Context view mode */
                                  <div className="space-y-3">
                                    {fetchingChunks[citation.document_id!] ? (
                                      <div className="flex items-center gap-2 py-4 justify-center text-muted-foreground text-xs">
                                        <Loader2 className="w-4 h-4 animate-spin text-primary" />
                                        <span>Đang tải ngữ cảnh...</span>
                                      </div>
                                    ) : !docChunks[citation.document_id!] || docChunks[citation.document_id!].length === 0 ? (
                                      <div className="text-xs text-muted-foreground py-2 text-center">
                                        Không thể tải ngữ cảnh của tài liệu này.
                                      </div>
                                    ) : (() => {
                                      const chunks = docChunks[citation.document_id!]
                                      
                                      // Find matching chunk
                                      const activeChunk = chunks.find(c => 
                                        c.id === citation.chunk_id || 
                                        c.content.includes(citation.content) || 
                                        citation.content.includes(c.content)
                                      )
                                      
                                      const targetPage = activeChunk?.metadata?.page_number || activeChunk?.metadata?.page || citation.page_number || 1
                                      
                                      const pageChunks = chunks.filter(c => {
                                        const p = c.metadata?.page_number || c.metadata?.page || 1
                                        return p === targetPage
                                      })
                                      
                                      pageChunks.sort((a, b) => a.chunk_index - b.chunk_index)
                                      
                                      return (
                                        <div className="space-y-2">
                                          <div className="flex items-center justify-between text-[11px] text-muted-foreground border-b pb-1 select-none font-sans font-medium">
                                            <span>Trang {targetPage}</span>
                                            <button
                                              onClick={() => {
                                                setPreviewDocId(citation.document_id!)
                                                setPreviewFilename(citation.title || citation.source || 'Tài liệu')
                                              }}
                                              className="text-primary hover:underline flex items-center gap-1 cursor-pointer font-semibold"
                                            >
                                              Mở bản gốc full ↗
                                            </button>
                                          </div>
                                          <div className="text-xs leading-relaxed text-foreground text-justify bg-muted/20 rounded-lg p-2.5 max-h-56 overflow-y-auto custom-scrollbar font-serif">
                                            {pageChunks.map((chunk) => {
                                              const isTarget = chunk.id === (activeChunk?.id || citation.chunk_id)
                                              return (
                                                <span
                                                  key={chunk.id}
                                                  className={cn(
                                                    "transition-colors rounded px-0.5",
                                                    isTarget
                                                      ? "bg-yellow-100 text-yellow-950 font-semibold ring-1 ring-yellow-300 dark:bg-yellow-950/60 dark:text-yellow-100 dark:ring-yellow-800"
                                                      : "text-foreground/80"
                                                  )}
                                                >
                                                  {chunk.content}{" "}
                                                </span>
                                              )
                                            })}
                                          </div>
                                        </div>
                                      )
                                    })()}
                                  </div>
                                )}

                                {isActive && (
                                  <div className="mt-3 pt-2.5 border-t border-primary/10">
                                    <p className="text-[10px] text-muted-foreground italic">
                                      ✦ Đây là nội dung được tham chiếu từ câu trả lời
                                    </p>
                                  </div>
                                )}
                                {citation.grounding_score !== undefined && (
                                  <div className="mt-3 pt-2.5 border-t">
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

      {previewDocId && (
        <DocumentPreviewDialog
          documentId={previewDocId}
          filename={previewFilename}
          isOpen={!!previewDocId}
          onClose={() => {
            setPreviewDocId(null)
            setPreviewFilename('')
          }}
        />
      )}
    </div>
  )
}
