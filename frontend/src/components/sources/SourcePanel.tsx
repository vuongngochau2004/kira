'use client'

import { useState, useEffect } from 'react'
import { BookOpen, ChevronLeft, ChevronRight, FileText, Globe } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { MOCK_SOURCES, MockSource } from './mock-sources'

interface SourcePanelProps {
  isOpen?: boolean
  onToggle?: () => void
}

const FILE_ICONS: Record<string, typeof FileText> = {
  pdf: FileText,
  docx: FileText,
  web: Globe,
}

export function SourcePanel({ isOpen = false, onToggle }: SourcePanelProps) {
  const [isExpanded, setIsExpanded] = useState(isOpen)
  const [sources] = useState<MockSource[]>(MOCK_SOURCES)

  useEffect(() => {
    setIsExpanded(isOpen)
  }, [isOpen])

  const handleToggle = () => {
    setIsExpanded(prev => !prev)
    onToggle?.()
  }

  return (
    <aside
      className={cn(
        'flex flex-col bg-background border-l transition-all duration-300 ease-in-out shrink-0',
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
            className="absolute -left-12 top-4 h-8 w-8 rounded-l-lg rounded-r-none border-y border-l border-r-0 bg-background"
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
          <div className="flex-1 overflow-y-auto min-h-0">
            <div className="p-4 space-y-3">
              {sources.map((source, index) => {
                const Icon = FILE_ICONS[source.type] || FileText

                return (
                  <div
                    key={source.id}
                    className="p-3 rounded-lg border bg-card hover:bg-muted/50 transition-colors cursor-pointer"
                  >
                    {/* Source Header */}
                    <div className="flex items-start gap-2 mb-2">
                      <div className="shrink-0 w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center">
                        <span className="text-xs font-semibold text-primary">
                          {index + 1}
                        </span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1 mb-1">
                          <Icon className="w-3 h-3 text-muted-foreground shrink-0" />
                          <h3 className="text-sm font-medium truncate">
                            {source.title}
                          </h3>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          {source.page && (
                            <span>Trang {source.page}</span>
                          )}
                          <span>·</span>
                          <span>Độ tương đồng {Math.round(source.score * 100)}%</span>
                        </div>
                      </div>
                    </div>

                    {/* Snippet */}
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {source.snippet}
                    </p>
                  </div>
                )
              })}
            </div>
          </div>
        </>
      )}
    </aside>
  )
}
