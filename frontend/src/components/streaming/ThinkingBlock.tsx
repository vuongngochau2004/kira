'use client'

import { useState, useEffect, useRef, useMemo, useCallback, memo } from 'react'
import { ChevronDown, Loader2, Check, Search, Globe } from 'lucide-react'
import { cn } from '@/lib/utils'

// ==================== Types ====================

export interface ThinkingStep {
  node: string
  status: 'pending' | 'running' | 'complete'
  duration?: number
  timestamp?: number
}

export interface ToolCall {
  id: string
  name: string
  displayName: string
  argument: string
  status: 'running' | 'complete'
  result?: string
}

interface ThinkingBlockProps {
  steps: ThinkingStep[]
  toolCalls?: ToolCall[]
  className?: string
  isLoading?: boolean
  streamingState?: 'connecting' | 'routing' | 'retrieving' | 'generating' | 'complete' | 'error'
  startTime?: number
}

// ==================== Helpers ====================

/** Extract the raw reasoning text from thinking steps */
function extractReasoning(steps: ThinkingStep[], includeAll: boolean = false): string {
  let reasoning = ''

  for (const step of steps) {
    const lines = step.node.split('\n')

    for (const rawLine of lines) {
      const line = rawLine.trim()
      if (!line) continue

      // Extract text from LLM Reasoning lines
      if (line.includes('LLM Reasoning:') || line.includes('↳ LLM Reasoning:')) {
        const reasoningText = line.replace(/↳ LLM Reasoning:|LLM Reasoning:/gi, '').trim()
        if (reasoningText) reasoning += (reasoning ? '\n' : '') + reasoningText
      }
      // When includeAll=true, include router and tool call info for streaming display
      else if (includeAll) {
        // Include all content during streaming
        reasoning += (reasoning ? '\n' : '') + line
      }
      // Skip router and tool call headers in completed state
      else if (
        line.includes('RAG') ||
        line.includes('Router') ||
        line.includes('Conversational') ||
        line.includes('Tool Call:') ||
        line.includes('↳ Tool Call:') ||
        line.startsWith('•')
      ) {
        continue
      }
      // General reasoning text
      else {
        reasoning += (reasoning ? '\n' : '') + line
      }
    }
  }

  return reasoning
}

/** Extract tool calls from thinking steps */
function extractToolCalls(steps: ThinkingStep[]): ToolCall[] {
  const tools: ToolCall[] = []

  for (const step of steps) {
    const lines = step.node.split('\n')
    let currentToolName = ''
    let currentToolLines: string[] = []

    for (const rawLine of lines) {
      const line = rawLine.trim()
      if (!line) continue

      if (line.includes('Tool Call:') || line.includes('↳ Tool Call:')) {
        // Save previous tool
        if (currentToolName) {
          tools.push({
            id: `tool-${tools.length}`,
            name: currentToolName.toLowerCase().replace(/\s+/g, '_'),
            displayName: currentToolName,
            argument: '',
            status: step.status === 'complete' ? 'complete' : 'running',
            result: currentToolLines.join('\n'),
          })
        }
        currentToolName = line.replace(/↳ Tool Call:|Tool Call:/gi, '').trim()
        currentToolLines = []
      } else if (currentToolName && (line.startsWith('•') || line.startsWith('  '))) {
        currentToolLines.push(line.replace(/^[•\s]+/, '').trim())
      }
    }

    // Save last tool
    if (currentToolName) {
      tools.push({
        id: `tool-${tools.length}`,
        name: currentToolName.toLowerCase().replace(/\s+/g, '_'),
        displayName: currentToolName,
        argument: '',
        status: step.status === 'complete' ? 'complete' : 'running',
        result: currentToolLines.join('\n'),
      })
    }
  }

  return tools
}

// ==================== Sub-components ====================

/** Elapsed time display with live counter */
function ElapsedTime({ startTime, isRunning }: { startTime: number; isRunning: boolean }) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!isRunning) {
      setElapsed(Math.round((Date.now() - startTime) / 1000))
      return
    }

    // Update immediately
    setElapsed(Math.round((Date.now() - startTime) / 1000))

    const interval = setInterval(() => {
      setElapsed(Math.round((Date.now() - startTime) / 1000))
    }, 1000)

    return () => clearInterval(interval)
  }, [startTime, isRunning])

  if (elapsed < 1) return null
  return <span>{elapsed}s</span>
}

/** Memoized elapsed time to prevent parent re-renders */
const MemoizedElapsedTime = memo(ElapsedTime)

/** Blinking cursor for streaming */
function StreamingCursor() {
  return (
    <span className="inline-block w-[2px] h-[1em] bg-zinc-400 dark:bg-zinc-500 animate-pulse ml-0.5 align-middle" />
  )
}

/** Memoized streaming cursor */
const MemoizedStreamingCursor = memo(StreamingCursor)

/** Tool call card */
function ToolCallCard({ tool }: { tool: ToolCall }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const isComplete = tool.status === 'complete'

  // Memoize toggle handler
  const handleToggle = useCallback(() => {
    setIsExpanded(prev => !prev)
  }, [])

  return (
    <div
      className={cn(
        'rounded-xl border transition-all duration-200',
        'border-zinc-200/60 dark:border-zinc-700/50',
        'bg-zinc-50/50 dark:bg-zinc-800/30',
        isExpanded && 'bg-zinc-50 dark:bg-zinc-800/50'
      )}
    >
      <button
        onClick={handleToggle}
        className={cn(
          'flex items-center gap-3 w-full px-4 py-3',
          'hover:bg-zinc-100/50 dark:hover:bg-zinc-700/20',
          'rounded-xl transition-colors duration-150',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/20'
        )}
      >
        {/* Status icon */}
        <div className="flex-shrink-0">
          {isComplete ? (
            <div className="w-5 h-5 rounded-full bg-emerald-500/15 dark:bg-emerald-500/20 flex items-center justify-center">
              <Check className="w-3 h-3 text-emerald-600 dark:text-emerald-400" strokeWidth={3} />
            </div>
          ) : (
            <Loader2 className="w-5 h-5 text-zinc-400 dark:text-zinc-500 animate-spin" />
          )}
        </div>

        {/* Tool info */}
        <div className="flex items-center gap-2 min-w-0 flex-1 text-left">
          <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-200 whitespace-nowrap">
            {tool.displayName}
          </span>
          {tool.argument && (
            <span className="text-sm text-zinc-500 dark:text-zinc-400 truncate">
              {tool.argument}
            </span>
          )}
          {tool.result && !tool.argument && (
            <span className="text-sm text-zinc-500 dark:text-zinc-400 truncate">
              {tool.result.split('\n')[0]}
            </span>
          )}
        </div>

        {/* Expand chevron */}
        {tool.result && (
          <ChevronDown
            className={cn(
              'w-4 h-4 text-zinc-400 dark:text-zinc-500 flex-shrink-0',
              'transition-transform duration-200',
              isExpanded && 'rotate-180'
            )}
          />
        )}
      </button>

      {/* Expandable content */}
      {isExpanded && tool.result && (
        <div className="px-4 pb-3 pt-0">
          <div className="pl-8">
            <pre className="text-xs text-zinc-500 dark:text-zinc-400 font-mono whitespace-pre-wrap leading-relaxed">
              {tool.result}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}

/** Memoized tool call card to prevent unnecessary re-renders */
const MemoizedToolCallCard = memo(ToolCallCard)

// ==================== Main Component ====================

export function ThinkingBlock({
  steps,
  toolCalls: externalToolCalls,
  className,
  isLoading = false,
  streamingState,
  startTime: externalStartTime,
}: ThinkingBlockProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const startTimeRef = useRef<number>(0)
  const hasStartedRef = useRef(false)

  // Capture start time once when loading begins
  useEffect(() => {
    if ((isLoading || streamingState) && !hasStartedRef.current) {
      startTimeRef.current = externalStartTime || Date.now()
      hasStartedRef.current = true
    }
    // Reset when complete for next message
    if (streamingState === 'complete' || streamingState === 'error') {
      hasStartedRef.current = false
    }
  }, [isLoading, streamingState, externalStartTime])

  // Auto-expand when streaming starts
  useEffect(() => {
    if (isLoading && streamingState && streamingState !== 'complete' && streamingState !== 'error') {
      setIsExpanded(true)
    }
  }, [isLoading, streamingState])

  // Determine if currently running (streaming)
  const isRunning = (
    isLoading &&
    streamingState !== 'complete' &&
    streamingState !== 'error'
  )

  // Extract reasoning and tools from steps
  // includeAll=true during streaming to show router/retrieval info
  const reasoning = useMemo(() => extractReasoning(steps, isRunning), [steps, isRunning])
  const parsedTools = useMemo(() => extractToolCalls(steps), [steps])

  const allToolCalls = useMemo(() => {
    if (externalToolCalls && externalToolCalls.length > 0) return externalToolCalls
    return parsedTools
  }, [externalToolCalls, parsedTools])

  // Show the block when loading OR when we have thinking data (for completed messages)
  const shouldShow = isLoading || steps.length > 0 || (streamingState && streamingState !== 'complete' && streamingState !== 'error')

  if (!shouldShow) return null

  return (
    <div className={cn('space-y-2 py-1', className)} aria-live="polite">
      {/* === Thinking Block === */}
      <div className={cn(
        'rounded-xl border transition-all duration-200',
        'border-zinc-200/60 dark:border-zinc-700/50',
        isExpanded
          ? 'bg-zinc-50/80 dark:bg-zinc-800/40'
          : 'bg-transparent'
      )}>
        {/* Header */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          aria-expanded={isExpanded}
          className={cn(
            'flex items-center gap-2.5 w-full px-4 py-2.5',
            'hover:bg-zinc-100/50 dark:hover:bg-zinc-700/20',
            'rounded-xl transition-colors duration-150',
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/20'
          )}
        >
          {/* Spinner / Dot indicator */}
          <div className="flex-shrink-0 w-4 h-4 flex items-center justify-center">
            {isRunning ? (
              <Loader2 className="w-4 h-4 text-zinc-500 dark:text-zinc-400 animate-spin" />
            ) : (
              <div className="w-2 h-2 rounded-full bg-zinc-400 dark:bg-zinc-500" />
            )}
          </div>

          {/* Label */}
          <span className="text-sm text-zinc-600 dark:text-zinc-300 font-medium">
            {isRunning ? (
              <>
                Thinking
                {startTimeRef.current > 0 && (
                  <span className="text-zinc-400 dark:text-zinc-500 ml-1">
                    <MemoizedElapsedTime startTime={startTimeRef.current} isRunning={true} />
                  </span>
                )}
              </>
            ) : (
              <>
                Thought for{' '}
                <MemoizedElapsedTime startTime={startTimeRef.current} isRunning={false} />
              </>
            )}
          </span>

          {/* Chevron */}
          <ChevronDown
            className={cn(
              'w-4 h-4 text-zinc-400 dark:text-zinc-500 ml-auto flex-shrink-0',
              'transition-transform duration-200',
              isExpanded && 'rotate-180'
            )}
          />
        </button>

        {/* Reasoning content area */}
        <div
          className={cn(
            'overflow-hidden transition-all duration-200 ease-out',
            isExpanded ? 'max-h-[600px] opacity-100' : 'max-h-0 opacity-0'
          )}
        >
          <div className="px-4 pb-4 border-t border-zinc-200/40 dark:border-zinc-700/30">
            <div className="pt-3 overflow-y-auto max-h-80">
              {reasoning ? (
                <pre className="text-[13px] text-zinc-500 dark:text-zinc-400 font-mono whitespace-pre-wrap leading-relaxed">
                  {reasoning}
                  {isRunning && <MemoizedStreamingCursor />}
                </pre>
              ) : isRunning ? (
                <div className="text-[13px] text-zinc-400 dark:text-zinc-500 font-mono">
                  <MemoizedStreamingCursor />
                </div>
              ) : (
                <p className="text-[13px] text-zinc-400 dark:text-zinc-500 italic">
                  Không có nội dung suy luận
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* === Tool Call Blocks === */}
      {allToolCalls.map((tool) => (
        <MemoizedToolCallCard key={tool.id} tool={tool} />
      ))}
    </div>
  )
}
