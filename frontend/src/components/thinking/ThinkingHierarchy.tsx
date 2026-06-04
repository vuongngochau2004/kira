'use client'

import { useState } from 'react'
import { ChevronDown, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ThinkingHierarchy, ExecutionThinking } from '@/types/thinking'

interface ThinkingHierarchyProps {
  hierarchy: ThinkingHierarchy
  className?: string
  defaultExpanded?: boolean
}

/**
 * AgentBlock - Individual agent thinking block
 * Shows agent name with nested tool calls inside
 */
interface AgentBlockProps {
  agentName: string
  execution: ExecutionThinking[]
  isRunning: boolean
}

function AgentBlock({ agentName, execution, isRunning }: AgentBlockProps) {
  const [isExpanded, setIsExpanded] = useState(true)

  if (!execution || execution.length === 0) return null

  return (
    <div className="my-2">
      {/* Agent Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          'w-full flex items-center gap-2 px-3 py-2',
          'hover:bg-muted/30 transition-colors'
        )}
      >
        <ChevronDown className={cn(
          'w-3.5 h-3.5 text-muted-foreground flex-shrink-0 transition-transform duration-200',
          !isExpanded && 'rotate-[-90deg]'
        )} />
        <span className="text-sm font-medium text-foreground">{agentName}</span>
        {isRunning && (
          <Loader2 className="w-3 h-3 text-muted-foreground animate-spin ml-auto" />
        )}
      </button>

      {/* Nested Tool Calls */}
      {isExpanded && (
        <div className="pl-5 pr-2 py-1 space-y-1">
          {execution.map((stage: ExecutionThinking, idx: number) => (
            <div key={idx} className="flex items-center gap-2 text-xs">
              <span className="text-muted-foreground/60">•</span>
              <span className="text-muted-foreground">
                Iteration {stage.iteration} · {stage.strategy} · {stage.docsRetrieved} docs
              </span>
              {stage.duration && (
                <span className="text-muted-foreground/50 ml-auto">
                  {stage.duration}ms
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/**
 * ThinkingHierarchy - Hierarchical thinking display
 * Main "Thought" block with nested Agent blocks containing Tool Calls
 */
export function ThinkingHierarchy({
  hierarchy,
  className,
  defaultExpanded = true,
}: ThinkingHierarchyProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)

  const hasRouting = !!hierarchy.routing
  const hasExecution = hierarchy.execution.length > 0
  const hasReasoning = !!hierarchy.reasoning?.content
  const isRunning = hierarchy.status === 'running'
  const isError = hierarchy.status === 'error'

  // Data-driven filter: Only render if there's actual thinking process
  const hasThinkingProcess = hasRouting || hasExecution || hasReasoning

  // CRITICAL FIX: Always render when running (loading state), even without data yet
  // This ensures optimistic messages show the thinking block immediately
  // Only skip if we have no data AND not running AND not error
  if (!hasThinkingProcess && !isError && !isRunning) {
    return null
  }

  // CRITICAL: When running but no data yet, render skeleton with loading state
  // This prevents thinking text from appearing outside the component
  if (isRunning && !hasThinkingProcess) {
    // Return skeleton block - will populate with real data when it arrives
    return (
      <div
        className={cn(
          'rounded-lg border overflow-hidden',
          'border-border/30',
          'transition-all duration-200 ease-out',
          className
        )}
      >
        <button className="flex items-center gap-3 w-full px-4 py-3">
          <Loader2 className="w-4 h-4 text-muted-foreground animate-spin flex-shrink-0" />
          <span className="text-sm font-medium text-foreground flex-1 text-left">
            Thinking...
          </span>
          <ChevronDown className="w-4 h-4 text-muted-foreground flex-shrink-0" />
        </button>
        {/* Empty content area that will populate when data arrives */}
        <div className="px-4 pb-3">
          <div className="text-sm text-muted-foreground italic px-3 py-2">
            <span className="inline-block w-1 h-4 bg-muted-foreground/40 animate-pulse ml-1 align-middle" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div
      className={cn(
        'rounded-lg border overflow-hidden',
        'border-border/30',
        'transition-all duration-200 ease-out',
        className
      )}
    >
      {/* Main Header - "Thought" */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          'flex items-center gap-3 w-full px-4 py-3',
          'hover:bg-muted/50 transition-colors duration-150',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40'
        )}
      >
        {/* Simple status indicator */}
        {isRunning ? (
          <Loader2 className="w-4 h-4 text-muted-foreground animate-spin flex-shrink-0" />
        ) : isError ? (
          <div className="w-2 h-2 rounded-full bg-destructive flex-shrink-0" />
        ) : (
          <div className="w-2 h-2 rounded-full bg-primary flex-shrink-0" />
        )}

        {/* Label */}
        <span className="text-sm font-medium text-foreground flex-1 text-left">
          Thought
        </span>

        {/* Chevron */}
        <ChevronDown
          className={cn(
            'w-4 h-4 text-muted-foreground flex-shrink-0 transition-transform duration-200',
            !isExpanded && 'rotate-[-90deg]'
          )}
        />
      </button>

      {/* Content area with nested structure */}
      <div
        className={cn(
          'overflow-hidden transition-all duration-300 ease-in-out',
          isExpanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'
        )}
      >
        <div className="px-4 pb-3">
          {/* Error message */}
          {isError && hierarchy.error && (
            <div className="px-3 py-2 text-sm text-muted-foreground">
              {hierarchy.error}
            </div>
          )}
          {/* Agent Blocks with nested Tool Calls */}
          {hasExecution && (
            <AgentBlock
              agentName="Agent"
              execution={hierarchy.execution}
              isRunning={isRunning}
            />
          )}

          {/* AI Reasoning Content */}
          {hasReasoning && (
            <div className="px-3 py-2">
              <div className="text-sm text-foreground leading-relaxed">
                <pre className="whitespace-pre-wrap font-sans">
                  {hierarchy.reasoning!.content}
                </pre>
                {isRunning && (
                  <span className="inline-block w-1 h-4 bg-muted-foreground/40 animate-pulse ml-1 align-middle" />
                )}
              </div>
            </div>
          )}

          {/* Empty state */}
          {!hasRouting && !hasExecution && !hasReasoning && isRunning && (
            <div className="text-sm text-muted-foreground italic px-3 py-2">
              Waiting for thinking data...
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
