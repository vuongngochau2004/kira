'use client'

import { BookOpen } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface SourceChunk {
  id: string
  chunk_id?: string  // Backend may provide chunk_id
  content: string
  score: number
  document_id?: string
  chunk_index?: number
}

interface SourceCitationProps {
  sources: SourceChunk[]
  onClick: () => void
  className?: string
}

export function SourceCitation({ sources, onClick, className }: SourceCitationProps) {
  if (sources.length === 0) return null

  // Group by document
  const byDocument = sources.reduce((acc, source) => {
    const docId = source.document_id || 'unknown'
    if (!acc[docId]) {
      acc[docId] = []
    }
    acc[docId].push(source)
    return acc
  }, {} as Record<string, SourceChunk[]>)

  const documentCount = Object.keys(byDocument).length
  const avgScore = sources.reduce((sum, s) => sum + s.score, 0) / sources.length

  return (
    <button
      onClick={onClick}
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium',
        'bg-muted hover:bg-muted/70 transition-colors',
        'text-muted-foreground hover:text-foreground',
        className
      )}
      title={`${sources.length} chunks from ${documentCount} documents`}
    >
      <BookOpen className="w-3.5 h-3.5" />
      <span>📚 {sources.length} nguồn</span>
      {avgScore > 0.8 && (
        <span className="text-green-600 dark:text-green-400">•</span>
      )}
    </button>
  )
}
