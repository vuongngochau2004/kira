'use client'

import { useState, useEffect, useMemo, useRef } from 'react'
import { ChevronDown, ChevronRight, Loader2, Bot, Search, Brain, Zap, Database } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface ThinkingStep {
  node: string
  status: 'pending' | 'running' | 'complete'
  duration?: number
  timestamp?: number
}

interface ThinkingBlockProps {
  steps: ThinkingStep[]
  className?: string
  isLoading?: boolean
  streamingState?: 'connecting' | 'routing' | 'retrieving' | 'generating' | 'complete' | 'error'
}

// Section types matching Claude's thinking hierarchy
interface ThinkingSection {
  id: string
  type: 'router' | 'tool' | 'reasoning'
  title: string
  icon: typeof Bot
  status: 'pending' | 'running' | 'complete'
  content: string
  items: string[]
  isNew?: boolean
}

// Parse thinking data into structured sections (Claude-style)
function parseThinkingData(steps: ThinkingStep[]): ThinkingSection[] {
  const sections: ThinkingSection[] = []

  for (const step of steps) {
    const lines = step.node.split('\n').map(l => l.trim()).filter(l => l)
    if (lines.length === 0) continue

    const firstLine = lines[0]
    let currentSection: ThinkingSection | null = null

    // Detect Router section
    if (firstLine.includes('RAG') || firstLine.includes('Router') || firstLine.includes('Conversational')) {
      currentSection = {
        id: 'router',
        type: 'router',
        title: firstLine.includes('Conversational') ? 'Conversational Router' : 'RAG Router',
        icon: Bot,
        status: step.status,
        content: '',
        items: [],
        isNew: false
      }
      sections.push(currentSection)
    }

    // Parse remaining lines for sub-sections
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i]

      // Detect Tool Call section
      if (line.includes('Tool Call:') || line.includes('↳ Tool Call:')) {
        const toolName = line.replace(/↳ Tool Call:|Tool Call:/gi, '').trim()
        const toolSection: ThinkingSection = {
          id: `tool-${toolName.toLowerCase().replace(/\s+/g, '-')}`,
          type: 'tool',
          title: toolName,
          icon: Search,
          status: step.status,
          content: '',
          items: [],
          isNew: false
        }

        // Collect tool details
        let j = i + 1
        while (j < lines.length && (lines[j].startsWith('•') || lines[j].startsWith('  '))) {
          const detailLine = lines[j].replace(/^[•\s]+/, '').trim()
          toolSection.items.push(detailLine)
          toolSection.content += (toolSection.content ? '\n' : '') + detailLine
          j++
        }

        if (currentSection) {
          sections.push(toolSection)
        }

        i = j - 1
      }

      // Detect Reasoning section
      else if (line.includes('LLM Reasoning:') || line.includes('↳ LLM Reasoning:')) {
        const reasoningText = line
          .replace(/↳ LLM Reasoning:|LLM Reasoning:/gi, '')
          .trim()

        const reasoningSection: ThinkingSection = {
          id: 'reasoning',
          type: 'reasoning',
          title: 'LLM Reasoning',
          icon: Brain,
          status: step.status,
          content: reasoningText || '',
          items: reasoningText ? [reasoningText] : [],
          isNew: false
        }

        sections.push(reasoningSection)
      }

      // Add retrieval details to current tool section
      else if (line.match(/Iteration \d+|Strategy:|Retrieved:/)) {
        if (currentSection?.type === 'tool' || currentSection?.type === 'router') {
          currentSection.items.push(line)
          currentSection.content += (currentSection.content ? '\n' : '') + line
        }
      }

      // Reasoning lines
      else if (line && !line.startsWith('↳')) {
        const reasoningSection = sections.find(s => s.type === 'reasoning')
        if (reasoningSection) {
          reasoningSection.items.push(line)
          reasoningSection.content += (reasoningSection.content ? '\n' : '') + line
        }
      }
    }
  }

  return sections
}

// Respects reduced-motion preference
const useReducedMotion = () => {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false)
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    setPrefersReducedMotion(mediaQuery.matches)
    const handler = () => setPrefersReducedMotion(mediaQuery.matches)
    mediaQuery.addEventListener('change', handler)
    return () => mediaQuery.removeEventListener('change', handler)
  }, [])
  return prefersReducedMotion
}

export function ThinkingBlock({
  steps,
  className,
  isLoading = false,
  streamingState
}: ThinkingBlockProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const prefersReducedMotion = useReducedMotion()

  // Track steps for animation
  const prevStepsLengthRef = useRef(0)
  const [animatingSectionId, setAnimatingSectionId] = useState<string | null>(null)

  // Track streaming state changes for animation
  const prevStreamingStateRef = useRef<string | undefined>(undefined)

  // Parse thinking data into structured sections
  const sections = useMemo(() => {
    const parsed = parseThinkingData(steps)

    // Detect new sections for animation - compare with previous length
    if (parsed.length > prevStepsLengthRef.current) {
      // New section added - use the last one as the new section
      const newSection = parsed[parsed.length - 1]
      if (newSection) {
        setAnimatingSectionId(newSection.id)
        setTimeout(() => setAnimatingSectionId(null), 400)
      }
    }

    prevStepsLengthRef.current = parsed.length
    return parsed
  }, [steps])

  const isRunning = useMemo(
    () => steps.some((s) => s.status === 'running') || isLoading || streamingState === 'routing' || streamingState === 'retrieving',
    [steps, isLoading, streamingState]
  )

  const isComplete = useMemo(
    () => steps.length > 0 && steps.every((s) => s.status === 'complete') && streamingState === 'complete',
    [steps, streamingState]
  )

  // Auto-expand when streaming starts (KHÔNG auto-collapse khi complete)
  useEffect(() => {
    if (isRunning && !isExpanded) {
      setIsExpanded(true)
    }

    // Track streaming state changes for visual feedback
    if (prevStreamingStateRef.current !== streamingState) {
      prevStreamingStateRef.current = streamingState
    }
  }, [isRunning, isExpanded, streamingState])

  const handleToggle = () => setIsExpanded(!isExpanded)

  // Don't show if no data and not loading
  if (sections.length === 0 && !isLoading && !streamingState) return null

  const transitionDuration = prefersReducedMotion ? '0ms' : '200ms'

  // Get primary section for header
  const primarySection = sections[0]
  const PrimaryIcon = primarySection?.icon || Bot

  // Get status text based on streaming state
  const getStatusText = () => {
    if (isComplete) return 'Đã hoàn thành suy luận'
    if (streamingState === 'connecting') return 'Đang kết nối...'
    if (streamingState === 'routing') return 'Đã nhận câu hỏi...'
    if (streamingState === 'retrieving') return 'Đang tìm kiếm tài liệu...'
    if (streamingState === 'generating') return 'Đang suy luận...'
    if (isRunning) return 'Đang suy luận...'
    return primarySection?.title || 'Suy luận'
  }

  // Get status icon color based on state
  const getStatusColor = () => {
    if (streamingState === 'error') return 'bg-red-500'
    if (isComplete) return 'bg-green-500'
    if (streamingState === 'generating') return 'bg-blue-500'
    if (streamingState === 'retrieving') return 'bg-amber-500'
    if (streamingState === 'routing') return 'bg-indigo-500'
    return 'bg-zinc-300 dark:bg-zinc-600'
  }

  return (
    <div className={cn('py-2', className)} aria-live="polite">
      {/* Main Header - Claude-style with streaming states */}
      <button
        onClick={handleToggle}
        aria-expanded={isExpanded}
        aria-controls="thinking-content"
        className={cn(
          'group flex items-center gap-2 w-full',
          'min-h-[40px] px-2 py-2 -mx-2 rounded-lg',
          'hover:bg-zinc-50 dark:hover:bg-zinc-900/30',
          'active:scale-[0.98] transition-transform duration-150',
          'transition-colors duration-150',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/20'
        )}
      >
        {/* Status Indicator with state-based colors */}
        <div className="relative w-5 h-5 flex items-center justify-center shrink-0">
          {streamingState === 'connecting' || streamingState === 'routing' ? (
            <div className={cn(
              'w-2.5 h-2.5 rounded-full',
              'animate-pulse',
              getStatusColor()
            )} aria-hidden="true" />
          ) : isRunning && !isComplete ? (
            <Loader2 className="w-4 h-4 text-zinc-500 dark:text-zinc-400 animate-spin" aria-hidden="true" />
          ) : (
            <div className={cn('w-2.5 h-2.5 rounded-full', getStatusColor())} aria-hidden="true" />
          )}
        </div>

        {/* Icon and Title with streaming state */}
        <PrimaryIcon className={cn(
          'w-4 h-4 shrink-0 transition-colors duration-300',
          streamingState === 'generating' ? 'text-blue-500 dark:text-blue-400' :
          streamingState === 'retrieving' ? 'text-amber-500 dark:text-amber-400' :
          streamingState === 'routing' ? 'text-indigo-500 dark:text-indigo-400' :
          'text-zinc-600 dark:text-zinc-400'
        )} aria-hidden="true" />
        <span className={cn(
          'text-sm font-medium transition-colors duration-300',
          isComplete ? 'text-zinc-900 dark:text-zinc-100' :
          streamingState === 'error' ? 'text-red-600 dark:text-red-400' :
          'text-zinc-700 dark:text-zinc-300'
        )}>
          {getStatusText()}
        </span>

        {/* Chevron */}
        <div className="ml-auto">
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-zinc-400 dark:text-zinc-500" aria-hidden="true" />
          ) : (
            <ChevronRight className="w-4 h-4 text-zinc-400 dark:text-zinc-500" aria-hidden="true" />
          )}
        </div>
      </button>

      {/* Content Area - Claude-style nested blocks with streaming feedback */}
      <div
        id="thinking-content"
        role="region"
        aria-labelledby="thinking-header"
        className={cn(
          'overflow-hidden transition-all ease-out',
          !prefersReducedMotion && `duration-[${transitionDuration}]`,
          isExpanded ? 'max-h-96 opacity-100 mt-2' : 'max-h-0 opacity-0'
        )}
      >
        <div className="space-y-1">
          {sections.map((section) => (
            <div
              key={section.id}
              className={cn(
                !prefersReducedMotion && animatingSectionId === section.id && 'animate-in fade-in slide-in-from-bottom-2 duration-300'
              )}
            >
              <ThinkingSectionBlock
                section={section}
                prefersReducedMotion={prefersReducedMotion}
                level={0}
                streamingState={streamingState}
              />
            </div>
          ))}

          {/* Streaming State Placeholder */}
          {isRunning && sections.length === 0 && (
            <div className="flex items-center gap-2 py-2 pl-7 text-sm text-zinc-500 dark:text-zinc-400">
              {streamingState === 'connecting' ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
                  <span>Đang kết nối...</span>
                </>
              ) : streamingState === 'routing' ? (
                <>
                  <Bot className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>Đã nhận câu hỏi...</span>
                </>
              ) : streamingState === 'retrieving' ? (
                <>
                  <Database className="w-3.5 h-3.5 animate-pulse" aria-hidden="true" />
                  <span>Đang tìm kiếm tài liệu...</span>
                </>
              ) : streamingState === 'generating' ? (
                <>
                  <Brain className="w-3.5 h-3.5 animate-pulse" aria-hidden="true" />
                  <span>Đang suy luận...</span>
                </>
              ) : (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
                  <span>Đang phân tích câu hỏi...</span>
                </>
              )}
            </div>
          )}

          {/* Active Generation Indicator */}
          {streamingState === 'generating' && sections.length > 0 && (
            <div className="flex items-center gap-2 py-2 pl-7 text-sm text-blue-600 dark:text-blue-400">
              <Zap className="w-3.5 h-3.5 animate-pulse" aria-hidden="true" />
              <span>Đang tạo câu trả lời...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

interface ThinkingSectionBlockProps {
  section: ThinkingSection
  prefersReducedMotion: boolean
  level: number
  streamingState?: 'connecting' | 'routing' | 'retrieving' | 'generating' | 'complete' | 'error'
}

function ThinkingSectionBlock({ section, prefersReducedMotion, level, streamingState }: ThinkingSectionBlockProps) {
  const [isExpanded, setIsExpanded] = useState(true)
  const transitionDuration = prefersReducedMotion ? '0ms' : '200ms'
  const Icon = section.icon

  // Determine if this section is currently active based on streaming state
  const isCurrentlyActive = useMemo(() => {
    if (section.type === 'router') {
      return streamingState === 'routing'
    }
    if (section.type === 'tool') {
      return streamingState === 'retrieving'
    }
    if (section.type === 'reasoning') {
      return streamingState === 'generating'
    }
    return section.status === 'running'
  }, [section.type, section.status, streamingState])

  // Style based on section type and active state
  const typeStyles = useMemo(() => ({
    router: {
      icon: isCurrentlyActive
        ? 'text-indigo-500 dark:text-indigo-400 animate-pulse'
        : 'text-indigo-600 dark:text-indigo-400',
      title: isCurrentlyActive
        ? 'text-indigo-600 dark:text-indigo-300 font-medium'
        : 'text-indigo-700 dark:text-indigo-300 font-medium',
      border: isCurrentlyActive
        ? 'border-indigo-300 dark:border-indigo-700/60 bg-indigo-50/30 dark:bg-indigo-900/10'
        : 'border-indigo-200 dark:border-indigo-800/50'
    },
    tool: {
      icon: isCurrentlyActive
        ? 'text-emerald-500 dark:text-emerald-400 animate-pulse'
        : 'text-emerald-600 dark:text-emerald-400',
      title: isCurrentlyActive
        ? 'text-emerald-600 dark:text-emerald-300 font-medium'
        : 'text-emerald-700 dark:text-emerald-300 font-medium',
      border: isCurrentlyActive
        ? 'border-emerald-300 dark:border-emerald-700/60 bg-emerald-50/30 dark:bg-emerald-900/10'
        : 'border-emerald-200 dark:border-emerald-800/50'
    },
    reasoning: {
      icon: isCurrentlyActive
        ? 'text-amber-500 dark:text-amber-400 animate-pulse'
        : 'text-amber-600 dark:text-amber-400',
      title: isCurrentlyActive
        ? 'text-amber-600 dark:text-amber-300 font-medium'
        : 'text-amber-700 dark:text-amber-300 font-medium',
      border: isCurrentlyActive
        ? 'border-amber-300 dark:border-amber-700/60 bg-amber-50/30 dark:bg-amber-900/10'
        : 'border-amber-200 dark:border-amber-800/50'
    }
  }), [isCurrentlyActive])

  const styles = typeStyles[section.type]

  return (
    <div className={cn(
      'border-l-2 rounded-r transition-all duration-300',
      styles.border,
      level === 0 ? 'ml-0 pl-3' : 'ml-0 pl-2',
      isCurrentlyActive && 'shadow-sm'
    )}>
      {/* Section Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
        className={cn(
          'flex items-center gap-1.5 w-full',
          'min-h-[32px] px-1.5 py-1 -mx-1.5 rounded',
          'hover:bg-zinc-50 dark:hover:bg-zinc-900/20',
          'transition-colors duration-150',
          'focus:outline-none focus-visible:ring-1 focus-visible:ring-zinc-300/50'
        )}
      >
        {/* Chevron for expand/collapse */}
        {isExpanded ? (
          <ChevronDown className="w-3.5 h-3.5 text-zinc-400 dark:text-zinc-500 flex-shrink-0" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-zinc-400 dark:text-zinc-500 flex-shrink-0" />
        )}

        {/* Icon */}
        <Icon className={cn('w-3.5 h-3.5 flex-shrink-0', styles.icon)} />

        {/* Title */}
        <span className={cn('text-sm', styles.title)}>
          {section.title}
        </span>

        {/* Running indicator */}
        {(section.status === 'running' || isCurrentlyActive) && (
          <Loader2 className="w-3 h-3 text-zinc-400 animate-spin ml-auto" />
        )}
      </button>

      {/* Section Content */}
      <div
        className={cn(
          'overflow-hidden transition-all ease-out',
          !prefersReducedMotion && `duration-[${transitionDuration}]`,
          isExpanded ? 'max-h-64 opacity-100 mt-1.5' : 'max-h-0 opacity-0'
        )}
      >
        {/* Content text */}
        {section.content && (
          <div className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed whitespace-pre-wrap">
            {section.content}
          </div>
        )}

        {/* Items list */}
        {section.items.length > 0 && !section.content && (
          <div className="space-y-1">
            {section.items.map((item, idx) => (
              <div key={idx} className="flex items-start gap-2 text-sm text-zinc-600 dark:text-zinc-400">
                <span className="text-zinc-400 dark:text-zinc-500 mt-0.5">•</span>
                <span className="leading-relaxed">{item}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
