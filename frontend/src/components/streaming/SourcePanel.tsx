'use client'

import { useState, useRef, useEffect } from 'react'
import { X, Search, FileText, Loader2, Eye } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { SourceChunk } from './SourceCitation'

interface SourcePanelProps {
  sources: SourceChunk[]
  isOpen: boolean
  onClose: () => void
  activeSourceId?: string | null
  className?: string
}

export function SourcePanel({ sources, isOpen, onClose, activeSourceId, className }: SourcePanelProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())
  const [loadingIds, setLoadingIds] = useState<Set<string>>(new Set())
  const activeRef = useRef<HTMLDivElement>(null)

  // Auto-expand active source and scroll into view
  useEffect(() => {
    if (isOpen && activeSourceId) {
      setExpandedIds((prev) => {
        const next = new Set(prev)
        if (!next.has(activeSourceId)) {
          next.add(activeSourceId)
          // Simulate lazy loading
          setLoadingIds((load) => new Set(load).add(activeSourceId))
          setTimeout(() => {
            setLoadingIds((load) => {
              const nextLoad = new Set(load)
              nextLoad.delete(activeSourceId)
              return nextLoad
            })
          }, 300)
        }
        return next
      })
      // Scroll to active source
      setTimeout(() => {
        activeRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }, 400)
    }
  }, [isOpen, activeSourceId])

  if (!isOpen) return null

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
        // Simulate lazy loading
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
          <span className="text-muted-foreground text-xs">({sources.length})</span>
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
        {sources.map((source, index) => {
          const sourceKey = source.id || `source-${index}`
          const isExpanded = expandedIds.has(sourceKey)
          const isLoading = loadingIds.has(sourceKey)
          const isActive = sourceKey === activeSourceId

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
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm truncate">
                      #{index + 1}
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
                    {source.score && (
                      <span className={cn(
                        'text-xs px-1.5 py-0.5 rounded',
                        source.score > 0.8
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                          : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                      )}>
                        {(source.score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                  {!isExpanded && (
                    <p className="text-muted-foreground text-xs line-clamp-2 mt-1">
                      {source.content}
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
                      <p className="whitespace-pre-wrap">{source.content}</p>
                      {isActive && (
                        <div className="mt-3 pt-3 border-t border-primary/20">
                          <p className="text-xs text-muted-foreground italic">
                            ✦ Đây là nội dung được tham chiếu từ câu trả lời
                          </p>
                        </div>
                      )}
                    </>
                  )}
                  {source.chunk_index !== undefined && (
                    <p className="text-muted-foreground text-xs mt-2">
                      Chunk #{source.chunk_index}
                    </p>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
