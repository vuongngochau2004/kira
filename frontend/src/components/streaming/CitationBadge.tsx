'use client'

import { memo } from 'react'
import { CheckCircle, AlertTriangle, XCircle, HelpCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface CitationBadgeProps {
  chunkId: string
  verified?: boolean
  groundingScore?: number
  onClick?: () => void
  className?: string
  variant?: 'inline' | 'compact'
}

/**
 * CitationBadge component for displaying inline citation markers.
 *
 * Displays [source:chunk_id] markers with verification status indicators.
 * Color-coded by status:
 * - Green: Verified (grounding_score >= threshold)
 * - Yellow: Weak grounding (low similarity)
 * - Red: Hallucinated (chunk_id not in retrieved docs)
 * - Gray: Unknown/Checking
 */
export const CitationBadge = memo(({
  chunkId,
  verified = true,
  groundingScore,
  onClick,
  className,
  variant = 'inline'
}: CitationBadgeProps) => {
  // Determine status based on grounding score
  const getStatus = () => {
    if (groundingScore === undefined) return 'unknown'
    if (groundingScore >= 0.7) return 'verified'
    if (groundingScore >= 0.4) return 'weak'
    return 'hallucinated'
  }

  const status = getStatus()

  // Status icon mapping
  const StatusIcon = {
    verified: CheckCircle,
    weak: AlertTriangle,
    hallucinated: XCircle,
    unknown: HelpCircle
  }[status]

  // Color mapping
  const colors = {
    verified: 'bg-green-100 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-700',
    weak: 'bg-yellow-100 text-yellow-700 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-700',
    hallucinated: 'bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-700',
    unknown: 'bg-gray-100 text-gray-700 border-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700'
  }[status]

  const Icon = StatusIcon

  if (variant === 'compact') {
    return (
      <button
        onClick={onClick}
        className={cn(
          'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-mono font-medium border transition-colors',
          'hover:opacity-80 cursor-pointer',
          colors,
          className
        )}
        title={`Nguồn: ${chunkId}${groundingScore !== undefined ? ` (${(groundingScore * 100).toFixed(0)}% tin cậy)` : ''}`}
      >
        <Icon className="w-3 h-3" />
        <span>{chunkId}</span>
      </button>
    )
  }

  return (
    <button
      onClick={onClick}
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-mono font-medium border transition-all',
        'hover:scale-105 hover:shadow-sm cursor-pointer',
        colors,
        className
      )}
      title={`Nguồn: ${chunkId}${groundingScore !== undefined ? ` (${(groundingScore * 100).toFixed(0)}% tin cậy)` : ''}`}
    >
      <Icon className="w-3.5 h-3.5" />
      <span className="font-semibold">source:</span>
      <span>{chunkId}</span>
      {groundingScore !== undefined && (
        <span className="ml-1 text-[10px] opacity-70">
          {(groundingScore * 100).toFixed(0)}%
        </span>
      )}
    </button>
  )
})

CitationBadge.displayName = 'CitationBadge'

/**
 * Hook to parse content and replace [source:chunk_id] with CitationBadge components
 */
export function parseContentWithCitations(
  content: string,
  citations: Array<{
    chunk_id: string
    source: string
    page_number?: number
    grounding_score?: number
  }>,
  onCitationClick?: (chunkId: string, citation: any) => void
): Array<string | React.ReactElement> {
  if (!content) return []

  // Clean up inline [source:...] citations along with any leading spaces as requested by user
  const cleanedContent = content.replace(/\s*\[source:[^\]]+\]/g, '')
  return [cleanedContent]
}
