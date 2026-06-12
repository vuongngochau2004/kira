'use client'

import { useState, useRef, useEffect, useMemo } from 'react'
import { X, Search, FileText, Loader2, Eye } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { SourceChunk } from './SourceCitation'
import { documentsAPI } from '@/lib/api/simple-client'
import { DocumentPreviewDialog } from '@/components/document-preview-dialog'

interface SourcePanelProps {
  sources: SourceChunk[]
  isOpen: boolean
  onClose: () => void
  activeSourceId?: string | null
  className?: string
}

interface GroupedSource {
  document_id: string | null
  title: string
  type: 'pdf' | 'docx' | 'web'
  maxScore: number
  chunks: Array<{
    id: string
    content: string
    chunk_index?: number
    score: number
  }>
}

function cleanStringForMatching(str: string): string {
  if (!str) return ''
  return str
    .toLowerCase()
    .replace(/[\s\r\n\t]+/g, ' ')
    .replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?"']/g, '')
    .trim()
}

function findLongestMatch(content: string, snippet: string): { index: number; length: number } | null {
  const cleanedC = content.toLowerCase()
  const cleanedS = snippet.toLowerCase()

  // Try exact match first
  const exactIdx = cleanedC.indexOf(cleanedS)
  if (exactIdx !== -1) {
    return { index: exactIdx, length: snippet.length }
  }

  // Find longest word sub-segment that matches
  const words = snippet.split(/\s+/).filter(Boolean)
  if (words.length === 0) return null

  // Check word segments of decreasing length
  for (let len = words.length - 1; len >= 3; len--) {
    for (let start = 0; start <= words.length - len; start++) {
      const subPhrase = words.slice(start, start + len).join(' ')
      const idx = cleanedC.indexOf(subPhrase.toLowerCase())
      if (idx !== -1) {
        return { index: idx, length: subPhrase.length }
      }
    }
  }

  return null
}

function renderHighlightedContent(content: string, snippets: string[], isSelected: boolean) {
  if (!snippets || snippets.length === 0) {
    return <span className={isSelected ? "font-bold bg-primary/30 px-0.5 rounded text-foreground" : ""}>{content}</span>
  }

  // Find the snippet with the best match in this content
  let bestMatch: { index: number; length: number } | null = null
  let matchedSnippetIndex = -1

  for (let i = 0; i < snippets.length; i++) {
    const match = findLongestMatch(content, snippets[i])
    if (match) {
      if (!bestMatch || match.length > bestMatch.length) {
        bestMatch = match
        matchedSnippetIndex = i
      }
    }
  }

  if (bestMatch && matchedSnippetIndex !== -1) {
    const index = bestMatch.index
    const length = bestMatch.length

    const before = content.substring(0, index)
    const match = content.substring(index, index + length)
    const after = content.substring(index + length)

    return (
      <span>
        {before}
        <strong className={cn(
          "font-bold text-foreground px-0.5 rounded",
          isSelected ? "bg-primary/45 ring-1 ring-primary/60" : "bg-primary/25"
        )}>
          {match}
        </strong>
        {after}
      </span>
    )
  }

  // If no match is found, render as normal text (or select highlight if active)
  return (
    <span className={isSelected ? "font-bold bg-primary/35 px-0.5 rounded ring-1 ring-primary/40 text-foreground" : ""}>
      {content}
    </span>
  )
}

export function SourcePanel({ sources, isOpen, onClose, activeSourceId, className }: SourcePanelProps) {
  const [expandedDocKeys, setExpandedDocKeys] = useState<Set<string>>(new Set())
  const [loadingIds, setLoadingIds] = useState<Set<string>>(new Set())
  const activeRef = useRef<HTMLDivElement>(null)
  
  const [docChunks, setDocChunks] = useState<Record<string, Array<{ id: string; chunk_index: number; content: string; metadata?: any }>>>({})
  const [fetchingDocIds, setFetchingDocIds] = useState<Set<string>>(new Set())

  // Modal preview state for mobile
  const [previewDocId, setPreviewDocId] = useState<string | null>(null)
  const [previewFilename, setPreviewFilename] = useState<string>('')

  // Group sources by document
  const groupedSources = useMemo(() => {
    const groups: Record<string, GroupedSource> = {}
    
    sources.forEach((source) => {
      const title = source.title || 'Tài liệu'
      const type = source.type || 'pdf'
      const key = source.document_id || title
      
      if (!groups[key]) {
        groups[key] = {
          document_id: source.document_id || null,
          title,
          type,
          maxScore: source.score,
          chunks: []
        }
      }
      
      groups[key].chunks.push({
        id: source.id,
        content: source.content,
        chunk_index: source.chunk_index,
        score: source.score
      })
      
      if (source.score > groups[key].maxScore) {
        groups[key].maxScore = source.score
      }
    })
    
    return Object.values(groups)
  }, [sources])

  // Auto-expand active source and scroll into view
  useEffect(() => {
    if (isOpen && activeSourceId) {
      const activeSource = sources.find(s => s.id === activeSourceId)
      if (activeSource) {
        const docKey = activeSource.document_id || activeSource.title || 'Tài liệu'
        setExpandedDocKeys((prev) => {
          const next = new Set(prev)
          next.add(docKey)
          return next
        })
        
        // Scroll to active source card
        setTimeout(() => {
          activeRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
        }, 400)
      }
    }
  }, [isOpen, activeSourceId, sources])

  // Load full document content when a document group is expanded
  useEffect(() => {
    expandedDocKeys.forEach((key) => {
      const group = groupedSources.find(g => (g.document_id || g.title) === key)
      if (group && group.document_id && docChunks[group.document_id] === undefined && !fetchingDocIds.has(group.document_id)) {
        const docId = group.document_id
        setFetchingDocIds((prev) => {
          const next = new Set(prev)
          next.add(docId)
          return next
        })
        documentsAPI.getChunks(docId)
          .then(chunks => {
            setDocChunks(prev => ({ ...prev, [docId]: chunks }))
          })
          .catch(err => {
            console.error('Failed to load chunks for mobile source panel:', err)
            // Mark as null to prevent infinite loop of retries on failure
            setDocChunks(prev => ({ ...prev, [docId]: null as any }))
          })
          .finally(() => {
            setFetchingDocIds((prev) => {
              const next = new Set(prev)
              next.delete(docId)
              return next
            })
          })
      }
    })
  }, [expandedDocKeys, groupedSources, docChunks, fetchingDocIds])

  // Scroll to active chunk on mobile when chunks are loaded
  useEffect(() => {
    expandedDocKeys.forEach((key) => {
      setTimeout(() => {
        const el = document.getElementById(`active-chunk-mobile-${key}`)
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
        }
      }, 300)
    })
  }, [expandedDocKeys, docChunks])

  if (!isOpen) return null

  const toggleExpand = (key: string) => {
    setExpandedDocKeys((prev) => {
      const next = new Set(prev)
      if (next.has(key)) {
        next.delete(key)
      } else {
        next.add(key)
      }
      return next
    })
  }

  return (
    <div className={cn(
      'fixed right-0 top-0 h-full w-80 border-l bg-background shadow-lg',
      'flex flex-col z-50 transition-transform',
      isOpen ? 'translate-x-0' : 'translate-x-full',
      className
    )}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <div className="flex items-center gap-2">
          <Search className="w-4 h-4 text-muted-foreground" />
          <h3 className="font-semibold">Nguồn tham khảo</h3>
          <span className="text-muted-foreground text-xs">({groupedSources.length})</span>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-muted rounded-md transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto divide-y">
        {groupedSources.map((group, index) => {
          const groupKey = group.document_id || group.title
          const isExpanded = expandedDocKeys.has(groupKey)
          const isActive = activeSourceId ? sources.find(s => s.id === activeSourceId)?.document_id === group.document_id : false

          return (
            <div
              key={groupKey}
              ref={isActive ? activeRef : null}
              className={cn(
                "p-3 transition-all",
                isActive && "bg-primary/5 border-l-2 border-primary"
              )}
            >
              {/* Outer Card converted to div to allow inner buttons without nesting errors */}
              <div
                onClick={() => toggleExpand(groupKey)}
                className="flex items-start gap-2 w-full text-left hover:bg-muted/50 rounded-md p-2 -m-2 cursor-pointer transition-colors"
              >
                <FileText className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm truncate text-foreground pr-2">
                      #{index + 1} {group.title}
                    </span>
                    {isActive && (
                      <span className={cn(
                        'inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded-full',
                        'bg-primary/20 text-primary font-medium'
                      )}>
                        <Eye className="w-3 h-3" />
                        Đang xem
                      </span>
                    )}
                    {group.maxScore && (
                      <span className={cn(
                        'text-xs px-1.5 py-0.5 rounded ml-auto shrink-0',
                        group.maxScore > 0.8
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                          : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                      )}>
                        {(group.maxScore * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-[10px] text-muted-foreground">
                    <span className="bg-primary/10 text-primary px-1.5 py-0.5 rounded font-medium">
                      {group.chunks.length} trích dẫn
                    </span>
                    {group.document_id && group.type === 'pdf' && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setPreviewDocId(group.document_id)
                          setPreviewFilename(group.title)
                        }}
                        className="inline-flex items-center gap-1 text-primary hover:text-primary/80 font-semibold transition-colors ml-2 cursor-pointer"
                      >
                        <Eye className="w-3 h-3" />
                        Xem bản gốc
                      </button>
                    )}
                  </div>
                  {!isExpanded && (
                    <p className="text-muted-foreground text-xs line-clamp-2 mt-1">
                      {group.chunks[0]?.content}
                    </p>
                  )}
                </div>
              </div>

              {isExpanded && (
                <div className={cn(
                  "ml-6 mt-2 text-sm text-foreground p-3 rounded-lg bg-muted/20 border border-muted",
                  isActive && "bg-primary/5 border-primary/20"
                )}>
                  <div className="mt-3 space-y-2.5 max-h-80 overflow-y-auto custom-scrollbar pr-1 select-text">
                    {group.chunks.map((c, chunkIdx) => {
                      const isExactCurrentSource = activeSourceId ? activeSourceId === c.id : false
                      return (
                        <div 
                          key={c.id || chunkIdx}
                          className={cn(
                            "text-xs leading-relaxed p-3 rounded-xl transition-all border",
                            isExactCurrentSource
                              ? "bg-primary/10 border-primary/30 text-foreground font-semibold shadow-sm"
                              : "bg-muted/30 border-border/50 text-muted-foreground hover:bg-muted hover:text-foreground"
                          )}
                        >
                          <div className="text-[10px] font-sans font-semibold text-primary/70 mb-1 select-none flex items-center justify-between">
                            <span>Trích dẫn #{chunkIdx + 1}</span>
                            {c.chunk_index !== undefined && <span>Trang {c.chunk_index + 1}</span>}
                          </div>
                          <p className="text-justify font-sans">{c.content}</p>
                        </div>
                      )
                    })}
                  </div>
                  
                  {isActive && (
                    <div className="mt-3 pt-3 border-t border-primary/20">
                      <p className="text-xs text-muted-foreground italic">
                        ✦ Đây là nội dung được tham chiếu từ câu trả lời
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
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
