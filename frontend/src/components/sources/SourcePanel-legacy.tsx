'use client'

import { useState, useEffect, useRef, useMemo } from 'react'
import { BookOpen, ChevronLeft, ChevronRight, FileText, Globe, Copy, Check, Loader2, ExternalLink, Download } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { useSourcesStore } from '@/lib/stores/sources-store'
import { documentsAPI } from '@/lib/api/simple-client'

interface SourcePanelProps {
  isOpen?: boolean
  onToggle?: () => void
}

const FILE_ICONS: Record<string, typeof FileText> = {
  pdf: FileText,
  docx: FileText,
  web: Globe,
}

interface GroupedSource {
  document_id: string | null
  title: string
  type: 'pdf' | 'docx' | 'web'
  maxScore: number
  chunks: Array<{
    id: string
    snippet: string
    page?: number
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

export function SourcePanel({ isOpen, onToggle }: SourcePanelProps) {
  const store = useSourcesStore()
  const isExpanded = isOpen !== undefined ? isOpen : store.isOpen
  const sources = store.sources

  const [expandedDocKey, setExpandedDocKey] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  
  const [docChunks, setDocChunks] = useState<Record<string, Array<{ id: string; chunk_index: number; content: string; metadata?: any }>>>({})
  const [loadingDocs, setLoadingDocs] = useState<Record<string, boolean>>({})

  // Interactive PDF/Document Preview States
  const [localActiveChunkId, setLocalActiveChunkId] = useState<string | null>(null)
  const [previewTab, setPreviewTab] = useState<'pdf' | 'text'>('pdf')

  const handleToggle = () => {
    if (onToggle) {
      onToggle()
    } else {
      store.toggleOpen()
    }
  }

  const groupedSources = useMemo(() => {
    const groups: Record<string, GroupedSource> = {}
    
    sources.forEach((source) => {
      const key = source.document_id || source.title
      
      if (!groups[key]) {
        groups[key] = {
          document_id: source.document_id || null,
          title: source.title,
          type: source.type,
          maxScore: source.score,
          chunks: []
        }
      }
      
      groups[key].chunks.push({
        id: source.id,
        snippet: source.snippet,
        page: source.page,
        score: source.score
      })
      
      if (source.score > groups[key].maxScore) {
        groups[key].maxScore = source.score
      }
    })
    
    return Object.values(groups)
  }, [sources])

  const activeGroup = useMemo(() => {
    return groupedSources.find(g => (g.document_id || g.title) === expandedDocKey)
  }, [groupedSources, expandedDocKey])

  // Reset local selection and set initial tab when document changes
  useEffect(() => {
    if (activeGroup) {
      setLocalActiveChunkId(null)
      setPreviewTab(activeGroup.type === 'pdf' ? 'pdf' : 'text')
    }
  }, [expandedDocKey, activeGroup])

  useEffect(() => {
    if (expandedDocKey) {
      if (activeGroup && activeGroup.document_id && docChunks[activeGroup.document_id] === undefined && !loadingDocs[activeGroup.document_id]) {
        const docId = activeGroup.document_id
        setLoadingDocs(prev => ({ ...prev, [docId]: true }))
        documentsAPI.getChunks(docId)
          .then(chunks => {
            setDocChunks(prev => ({ ...prev, [docId]: chunks }))
          })
          .catch(err => {
            console.warn('[SourcePanel] Failed to load document chunks (will fallback to RAG snippets):', err?.message || err)
            setDocChunks(prev => ({ ...prev, [docId]: null as any }))
          })
          .finally(() => {
            setLoadingDocs(prev => ({ ...prev, [docId]: false }))
          })
      }
    }
  }, [expandedDocKey, activeGroup, docChunks, loadingDocs])

  useEffect(() => {
    if (expandedDocKey) {
      setTimeout(() => {
        const el = document.getElementById(`active-chunk-${expandedDocKey}`)
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
        }
      }, 300)
    }
  }, [expandedDocKey, docChunks])

  useEffect(() => {
    if (store.activeSourceId) {
      const matchedSource = sources.find(s => s.id === store.activeSourceId)
      if (matchedSource) {
        const docKey = matchedSource.document_id || matchedSource.title
        setExpandedDocKey(docKey)
        setLocalActiveChunkId(store.activeSourceId) 
        
        const timer = setTimeout(() => {
          const cardElement = document.getElementById(`source-card-${docKey}`)
          if (cardElement) {
            cardElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
            cardElement.classList.add('ring-2', 'ring-primary/40')
            setTimeout(() => {
              cardElement.classList.remove('ring-2', 'ring-primary/40')
            }, 1500)
          }
        }, 150)

        return () => clearTimeout(timer)
      }
    }
  }, [store.activeSourceId, sources])

  const handleCardClick = (key: string) => {
    setExpandedDocKey(prev => prev === key ? null : key)
  }

  const handleCopy = async (e: React.MouseEvent, id: string, text: string) => {
    e.stopPropagation() 
    try {
      await navigator.clipboard.writeText(text)
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 2000)
    } catch (err) {}
  }

  const getCleanSearchPhrase = (snippet: string) => {
    if (!snippet) return ''
    const words = snippet
      .replace(/[^\p{L}\p{N}\s]/gu, ' ')
      .trim()
      .split(/\s+/)
      .filter(Boolean)
    return words.slice(0, 6).join(' ')
  }

  // Group chunks by page for structured preview
  const chunksByPage = useMemo(() => {
    if (!activeGroup) return {}
    const chunksList = docChunks[activeGroup.document_id || ''] || []
    
    const pages: Record<number, typeof chunksList> = {}
    chunksList.forEach(chunk => {
      const page = chunk.metadata?.page_number || chunk.metadata?.page || 1
      if (!pages[page]) {
        pages[page] = []
      }
      pages[page].push(chunk)
    })
    return pages
  }, [activeGroup, docChunks])

  // Find the active chunk details for preview
  const activeChunkInfo = useMemo(() => {
    if (!expandedDocKey || !activeGroup) return null

    const chunksList = docChunks[activeGroup.document_id || ''] || []
    
    // Find active chunk id (prefer local selection, then global store selection)
    let currentId = localActiveChunkId
    if (!currentId && store.activeSourceId) {
      // Check if global activeSourceId belongs to this group's chunks
      const belongs = activeGroup.chunks.some(c => c.id === store.activeSourceId) || 
                      chunksList.some(c => c.id === store.activeSourceId)
      if (belongs) {
        currentId = store.activeSourceId
      }
    }
    
    // If still no selection, fallback to the first chunk from the RAG chunks
    if (!currentId && activeGroup.chunks.length > 0) {
      currentId = activeGroup.chunks[0].id
    }

    // Now look up the chunk contents and page number
    let content = ''
    let page = 1
    let dbChunkId = ''
    let found = false

    if (currentId) {
      // 1. Try finding in full document chunks by exact ID
      const fullChunk = chunksList.find(c => c.id === currentId)
      if (fullChunk) {
        content = fullChunk.content
        page = fullChunk.metadata?.page_number || fullChunk.metadata?.page || 1
        dbChunkId = fullChunk.id
        found = true
      }
      
      // 2. Try finding in RAG chunks and locate corresponding database chunk by content
      if (!found) {
        const ragChunk = activeGroup.chunks.find(c => c.id === currentId)
        if (ragChunk) {
          content = ragChunk.snippet
          page = ragChunk.page || 1
          
          const matchedDbChunk = chunksList.find(c => {
            const cleanedS = cleanStringForMatching(ragChunk.snippet)
            const cleanedC = cleanStringForMatching(c.content)
            return cleanedS && cleanedC && (cleanedC.includes(cleanedS) || cleanedS.includes(cleanedC))
          })
          if (matchedDbChunk) {
            dbChunkId = matchedDbChunk.id
            page = matchedDbChunk.metadata?.page_number || matchedDbChunk.metadata?.page || page
          }
          found = true
        }
      }
    }

    // Fallback if not found
    if (!found && activeGroup.chunks.length > 0) {
      content = activeGroup.chunks[0].snippet
      page = activeGroup.chunks[0].page || 1
      
      const matchedDbChunk = chunksList.find(c => {
        const cleanedS = cleanStringForMatching(content)
        const cleanedC = cleanStringForMatching(c.content)
        return cleanedS && cleanedC && (cleanedC.includes(cleanedS) || cleanedS.includes(cleanedC))
      })
      if (matchedDbChunk) {
        dbChunkId = matchedDbChunk.id
        page = matchedDbChunk.metadata?.page_number || matchedDbChunk.metadata?.page || page
      }
    }

    return {
      id: currentId,
      dbChunkId,
      content,
      page,
      searchPhrase: getCleanSearchPhrase(content)
    }
  }, [expandedDocKey, activeGroup, docChunks, localActiveChunkId, store.activeSourceId])

  // Scroll to active chunk in Right Pane text viewer
  useEffect(() => {
    const targetId = activeChunkInfo?.dbChunkId || activeChunkInfo?.id
    if (previewTab === 'text' && targetId) {
      setTimeout(() => {
        const el = document.getElementById(`preview-chunk-${targetId}`)
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' })
        }
      }, 200)
    }
  }, [previewTab, activeChunkInfo?.id])

  return (
    <aside
      className={cn(
        'flex bg-background border-l transition-all duration-300 ease-in-out shrink-0 h-full overflow-hidden',
        isExpanded 
          ? (expandedDocKey ? 'w-[900px] max-w-[95vw]' : 'w-[320px]') 
          : 'w-0'
      )}
    >
      {/* Collapsed state - toggle button only */}
      {!isExpanded && (
        <div className="relative w-0">
          <Button
            variant="ghost"
            size="icon"
            onClick={handleToggle}
            className="absolute -left-12 top-4 h-8 w-8 rounded-l-lg rounded-r-none border-y border-l border-r-0 bg-background shadow-md z-10"
          >
            <ChevronLeft className="w-4 h-4" />
          </Button>
        </div>
      )}

      {/* Expanded state */}
      {isExpanded && (
        <>
          {/* Left Column */}
          <div className={cn(
            "flex flex-col h-full",
            expandedDocKey ? "w-[320px] shrink-0 border-r" : "w-[320px] flex-1"
          )}>
            {/* Header */}
            <div className="h-14 border-b flex items-center justify-between px-4 shrink-0">
              <div className="flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-primary" />
                <h2 className="text-sm font-semibold">Nguồn</h2>
                <span className="text-xs text-muted-foreground">
                  ({groupedSources.length})
                </span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={handleToggle}
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>

            {/* Sources List */}
            <div ref={containerRef} className="flex-1 overflow-y-auto min-h-0">
              {groupedSources.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-48 text-center px-4">
                  <BookOpen className="w-8 h-8 text-muted-foreground/40 mb-2" />
                  <p className="text-xs text-muted-foreground">Chưa có nguồn trích xuất cho cuộc hội thoại này.</p>
                </div>
              ) : (
                <div className="p-4 space-y-3">
                  {groupedSources.map((group, index) => {
                    const Icon = FILE_ICONS[group.type] || FileText
                    const groupKey = group.document_id || group.title
                    const isCardExpanded = expandedDocKey === groupKey

                    return (
                      <div
                        key={groupKey}
                        id={`source-card-${groupKey}`}
                        onClick={() => handleCardClick(groupKey)}
                        className={cn(
                          'p-3 rounded-lg border bg-card hover:bg-muted/30 transition-all duration-200 cursor-pointer flex flex-col',
                          isCardExpanded ? 'border-primary/30 shadow-sm ring-1 ring-primary/20' : 'hover:border-border'
                        )}
                      >
                        {/* Source Header */}
                        <div className="flex items-start gap-2">
                          <div className="shrink-0 w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center">
                            <span className="text-xs font-semibold text-primary">
                              {index + 1}
                            </span>
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1 mb-1">
                              <Icon className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                              <h3 className="text-xs font-semibold truncate text-foreground">
                                {group.title}
                              </h3>
                            </div>
                            <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                              <span className="bg-primary/10 text-primary px-1.5 py-0.5 rounded font-medium">
                                {group.chunks.length} trích dẫn
                              </span>
                              <span>·</span>
                              <span>Trùng khớp {Math.round(group.maxScore * 100)}%</span>
                            </div>
                          </div>
                        </div>

                        {/* Snippet Block */}
                        <div className="mt-2 text-xs text-muted-foreground relative">
                          {isCardExpanded ? (
                            <div className="mt-3 space-y-2.5 max-h-80 overflow-y-auto custom-scrollbar pr-1 select-text">
                              {group.chunks.map((c, chunkIdx) => {
                                const isExactCurrentSource = localActiveChunkId ? localActiveChunkId === c.id : store.activeSourceId === c.id
                                return (
                                  <div 
                                    key={c.id || chunkIdx}
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      setLocalActiveChunkId(c.id)
                                    }}
                                    className={cn(
                                      "text-xs leading-relaxed cursor-pointer p-3 rounded-xl transition-all border",
                                      isExactCurrentSource
                                        ? "bg-primary/10 border-primary/30 text-foreground font-semibold shadow-sm"
                                        : "bg-muted/30 border-border/50 text-muted-foreground hover:bg-muted hover:text-foreground"
                                    )}
                                  >
                                    <div className="text-[10px] font-sans font-semibold text-primary/70 mb-1 select-none flex items-center justify-between">
                                      <span>Trích dẫn #{chunkIdx + 1}</span>
                                      {c.page !== undefined && <span>Trang {c.page}</span>}
                                    </div>
                                    <p className="text-justify font-sans">{c.snippet}</p>
                                  </div>
                                )
                              })}
                            </div>
                          ) : (
                            <p className="leading-relaxed line-clamp-2">
                              {group.chunks[0]?.snippet}
                            </p>
                          )}

                          {/* Expanded details & Copy Action */}
                          {isCardExpanded && (
                            <div className="mt-3 pt-2.5 border-t border-muted flex items-center justify-between shrink-0">
                              <span className="text-[10px] text-muted-foreground font-mono">
                                RAG Citation {group.document_id ? "— Full Doc" : ""}
                              </span>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={(e) => handleCopy(e, groupKey, group.chunks.map(c => c.snippet).join('\n\n'))}
                                className="h-6 w-6 text-muted-foreground hover:text-foreground"
                                title="Sao chép tất cả trích dẫn"
                              >
                                {copiedId === groupKey ? (
                                  <Check className="w-3.5 h-3.5 text-green-500 animate-in fade-in zoom-in duration-200" />
                                ) : (
                                  <Copy className="w-3.5 h-3.5" />
                                )}
                              </Button>
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Right Column (Document previewer) */}
          {expandedDocKey && activeGroup && (
            <div className="flex-1 flex flex-col h-full bg-muted/5">
              {/* Header */}
              <div className="h-14 border-b flex items-center justify-between px-4 shrink-0 bg-background">
                <div className="flex items-center gap-2 min-w-0 pr-4">
                  <FileText className="w-4 h-4 text-primary shrink-0" />
                  <h3 className="text-sm font-semibold truncate text-foreground">
                    {activeGroup.title}
                  </h3>
                </div>
                
                {/* Quick Actions */}
                <div className="flex items-center gap-2 shrink-0">
                  {activeGroup.document_id && (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex items-center gap-1.5 h-8 text-xs font-medium"
                        asChild
                      >
                        <a
                          href={documentsAPI.getDownloadUrl(activeGroup.document_id)}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          Tab mới
                        </a>
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-foreground"
                        asChild
                      >
                        <a
                          href={documentsAPI.getDownloadUrl(activeGroup.document_id)}
                          download
                        >
                          <Download className="w-4 h-4" />
                        </a>
                      </Button>
                    </>
                  )}
                </div>
              </div>

              {/* Subheader with Tab Selectors */}
              <div className="px-4 py-2 border-b bg-background flex items-center justify-between gap-4 shrink-0">
                <div className="flex gap-1 bg-muted p-0.5 rounded-lg text-xs">
                  {activeGroup.type === 'pdf' && (
                    <button
                      onClick={() => setPreviewTab('pdf')}
                      className={cn(
                        "px-3 py-1 rounded-md transition-all font-medium",
                        previewTab === 'pdf'
                          ? "bg-background text-foreground shadow-sm"
                          : "text-muted-foreground hover:text-foreground"
                      )}
                    >
                      Tài liệu gốc (PDF)
                    </button>
                  )}
                  <button
                    onClick={() => setPreviewTab('text')}
                    className={cn(
                      "px-3 py-1 rounded-md transition-all font-medium",
                      previewTab === 'text' || activeGroup.type !== 'pdf'
                        ? "bg-background text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    )}
                  >
                    Văn bản đầy đủ
                  </button>
                </div>

                {/* Pagination / Chunk context info */}
                {activeChunkInfo && (
                  <span className="text-[10px] bg-primary/10 text-primary font-medium px-2.5 py-0.5 rounded-full font-mono">
                    Trang {activeChunkInfo.page} {activeChunkInfo.searchPhrase ? `• Tìm: "${activeChunkInfo.searchPhrase}"` : ''}
                  </span>
                )}
              </div>

              {/* Preview Container */}
              <div className="flex-1 min-h-0 bg-background relative overflow-hidden flex items-center justify-center">
                {previewTab === 'pdf' && activeGroup.type === 'pdf' && activeGroup.document_id && activeChunkInfo ? (
                  <iframe
                    src={`${documentsAPI.getDownloadUrl(activeGroup.document_id)}#page=${activeChunkInfo.page}${activeChunkInfo.searchPhrase ? `&search=${encodeURIComponent(activeChunkInfo.searchPhrase)}` : ''}`}
                    className="w-full h-full border-0 bg-background"
                    title={activeGroup.title}
                    key={`${activeGroup.document_id}-${activeChunkInfo.page}-${activeChunkInfo.searchPhrase}`} // Force iframe reload to update target page
                  />
                ) : (
                  /* Text reader / DOCX Fallback viewer */
                  <div className="w-full h-full overflow-y-auto p-6 bg-muted/10 flex flex-col items-center">
                    <div className="w-full max-w-2xl bg-background border shadow-md rounded-xl p-8 min-h-[95%] flex flex-col font-serif text-sm leading-relaxed text-foreground select-text relative">
                      <div className="border-b pb-4 mb-6 flex items-center justify-between text-xs font-sans text-muted-foreground shrink-0 select-none">
                        <span>{activeGroup.title}</span>
                        <span className="font-mono">
                          {activeGroup.type.toUpperCase()} DOCUMENT
                        </span>
                      </div>

                      <div className="flex-1 space-y-4">
                        {activeGroup.document_id && loadingDocs[activeGroup.document_id] ? (
                          <div className="flex items-center gap-2 py-8 justify-center text-muted-foreground font-sans">
                            <Loader2 className="w-4 h-4 animate-spin text-primary" />
                            <span>Đang tải văn bản...</span>
                          </div>
                        ) : activeGroup.document_id && docChunks[activeGroup.document_id] ? (
                          /* Group by page and render as flowing text */
                          <div className="space-y-6">
                            {Object.entries(chunksByPage).map(([pageNum, pageChunks]) => (
                              <div key={pageNum} className="space-y-2">
                                <h4 className="text-xs font-sans font-semibold text-muted-foreground select-none border-b pb-1">
                                  Trang {pageNum}
                                </h4>
                                <p className="indent-6 text-justify leading-relaxed">
                                  {pageChunks.map((chunk) => {
                                    const isSelected = activeChunkInfo?.dbChunkId === chunk.id || activeChunkInfo?.id === chunk.id
                                    return (
                                      <span
                                        key={chunk.id}
                                        id={`preview-chunk-${chunk.id}`}
                                        onClick={() => {
                                          const matchedRagChunk = activeGroup.chunks.find(c => {
                                            const cleanedS = cleanStringForMatching(c.snippet)
                                            const cleanedC = cleanStringForMatching(chunk.content)
                                            return cleanedS && cleanedC && (cleanedC.includes(cleanedS) || cleanedS.includes(cleanedC))
                                          })
                                          if (matchedRagChunk) {
                                            setLocalActiveChunkId(matchedRagChunk.id)
                                          } else {
                                            setLocalActiveChunkId(chunk.id)
                                          }
                                        }}
                                        className={cn(
                                          "transition-all cursor-pointer px-0.5 rounded",
                                          isSelected && "ring-1 ring-primary/30"
                                        )}
                                      >
                                        {renderHighlightedContent(
                                          chunk.content,
                                          activeChunkInfo?.content ? [activeChunkInfo.content] : [],
                                          isSelected
                                        )}{" "}
                                      </span>
                                    )
                                  })}
                                </p>
                              </div>
                            ))}
                          </div>
                        ) : (
                          activeGroup.chunks.map((c, chunkIdx) => {
                            const isSelected = activeChunkInfo?.id === c.id
                            return (
                              <div
                                key={c.id || chunkIdx}
                                className={cn(
                                  "p-3 rounded-lg border bg-primary/5 border-primary/20",
                                  isSelected && "bg-primary/10 border-primary"
                                )}
                              >
                                <div className="text-[10px] text-muted-foreground mb-1 font-sans select-none">
                                  Trích dẫn #{chunkIdx + 1} {c.page ? `• Trang ${c.page}` : ''}
                                </div>
                                <p className="indent-4 font-semibold text-foreground">
                                  {c.snippet}
                                </p>
                              </div>
                            )
                          })
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </aside>
  )
}
