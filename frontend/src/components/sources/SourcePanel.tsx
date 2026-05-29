'use client'

import { useState, useEffect, useRef } from 'react'
import { BookOpen, ChevronLeft, ChevronRight, FileText, Globe, Copy, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { useSourcesStore } from '@/lib/stores/sources-store'

interface SourcePanelProps {
  isOpen?: boolean
  onToggle?: () => void
}

const FILE_ICONS: Record<string, typeof FileText> = {
  pdf: FileText,
  docx: FileText,
  web: Globe,
}

export function SourcePanel({ isOpen, onToggle }: SourcePanelProps) {
  // Use Zustand store for sources and panel state, with fallback to props for backward-compatibility
  const store = useSourcesStore()
  const isExpanded = isOpen !== undefined ? isOpen : store.isOpen
  const sources = store.sources

  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const handleToggle = () => {
    if (onToggle) {
      onToggle()
    } else {
      store.toggleOpen()
    }
  }

  // Handle auto-scroll and automatic expansion when activeSourceId is updated globally
  useEffect(() => {
    if (store.activeSourceId) {
      setExpandedId(store.activeSourceId)
      
      // Allow DOM to render then scroll smoothly
      const timer = setTimeout(() => {
        const cardElement = document.getElementById(`source-card-${store.activeSourceId}`)
        if (cardElement) {
          cardElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
          
          // Add a subtle brief highlight animation
          cardElement.classList.add('ring-2', 'ring-primary/40')
          setTimeout(() => {
            cardElement.classList.remove('ring-2', 'ring-primary/40')
          }, 1500)
        }
      }, 150)

      return () => clearTimeout(timer)
    }
  }, [store.activeSourceId])

  const handleCardClick = (id: string) => {
    setExpandedId(prev => prev === id ? null : id)
    if (store.activeSourceId === id) {
      store.setActiveSourceId(null)
    }
  }

  const handleCopy = async (e: React.MouseEvent, id: string, text: string) => {
    e.stopPropagation() // Prevent toggling the card
    try {
      await navigator.clipboard.writeText(text)
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 2000)
    } catch (err) {
      console.error('Failed to copy text: ', err)
    }
  }

  return (
    <aside
      className={cn(
        'flex flex-col bg-background border-l transition-all duration-300 ease-in-out shrink-0 h-full',
        isExpanded ? 'w-[320px]' : 'w-0'
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
          {/* Header */}
          <div className="h-14 border-b flex items-center justify-between px-4 shrink-0">
            <div className="flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-primary" />
              <h2 className="text-sm font-semibold">Nguồn</h2>
              <span className="text-xs text-muted-foreground">
                ({sources.length})
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
            {sources.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-48 text-center px-4">
                <BookOpen className="w-8 h-8 text-muted-foreground/40 mb-2" />
                <p className="text-xs text-muted-foreground">Chưa có nguồn trích xuất cho cuộc hội thoại này.</p>
              </div>
            ) : (
              <div className="p-4 space-y-3">
                {sources.map((source, index) => {
                  const Icon = FILE_ICONS[source.type] || FileText
                  const isCardExpanded = expandedId === source.id

                  return (
                    <div
                      key={source.id}
                      id={`source-card-${source.id}`}
                      onClick={() => handleCardClick(source.id)}
                      className={cn(
                        'p-3 rounded-lg border bg-card hover:bg-muted/30 transition-all duration-200 cursor-pointer flex flex-col',
                        isCardExpanded ? 'border-primary/30 shadow-sm' : 'hover:border-border'
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
                            <Icon className="w-3 h-3 text-muted-foreground shrink-0" />
                            <h3 className="text-xs font-medium truncate">
                              {source.title}
                            </h3>
                          </div>
                          <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                            {source.page && (
                              <span>Trang {source.page}</span>
                            )}
                            <span>·</span>
                            <span>Độ tương đồng {Math.round(source.score * 100)}%</span>
                          </div>
                        </div>
                      </div>

                      {/* Snippet Block */}
                      <div className="mt-2 text-xs text-muted-foreground relative">
                        <p className={cn(
                          'leading-relaxed transition-all duration-300',
                          isCardExpanded ? 'whitespace-pre-wrap' : 'line-clamp-2'
                        )}>
                          {source.snippet}
                        </p>

                        {/* Expanded details & Copy Action */}
                        {isCardExpanded && (
                          <div className="mt-3 pt-2.5 border-t border-muted flex items-center justify-between shrink-0">
                            <span className="text-[10px] text-muted-foreground font-mono">
                              Văn bản gốc RAG
                            </span>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={(e) => handleCopy(e, source.id, source.snippet)}
                              className="h-6 w-6 text-muted-foreground hover:text-foreground"
                              title="Sao chép văn bản gốc"
                            >
                              {copiedId === source.id ? (
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
        </>
      )}
    </aside>
  )
}
