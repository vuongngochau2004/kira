'use client'

import { useState, useEffect, useMemo } from 'react'
import { ChevronDown, ChevronRight, Sparkles, Circle, CheckCircle2 } from 'lucide-react'
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
}

export function ThinkingBlock({ steps, className, isLoading = false }: ThinkingBlockProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const isRunning = useMemo(
    () => steps.some((s) => s.status === 'running') || isLoading,
    [steps, isLoading]
  )

  const isComplete = useMemo(
    () => steps.length > 0 && steps.every((s) => s.status === 'complete'),
    [steps]
  )

  useEffect(() => {
    if (isRunning && !isExpanded) {
      setIsExpanded(true)
    }
  }, [isRunning])

  const handleToggle = () => setIsExpanded(!isExpanded)

  if (steps.length === 0 && !isLoading) return null

  return (
    <div className={cn('py-2', className)}>
      {/* Header */}
      <button
        onClick={handleToggle}
        className="flex items-center gap-2 text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors"
      >
        {/* Sparkles icon with animation when running */}
        <div className="relative w-4 h-4 flex items-center justify-center">
          {isRunning && (
            <div className="absolute inset-0 rounded-full bg-amber-500/20 animate-ping" />
          )}
          <Sparkles className={cn(
            'w-3.5 h-3.5 relative z-10',
            isRunning ? 'text-amber-500' : 'text-zinc-400'
          )} />
        </div>

        <span className="text-sm font-medium">Thinking</span>

        <ChevronDown
          className={cn(
            'w-4 h-4 transition-transform duration-200',
            !isExpanded && '-rotate-90'
          )}
        />
      </button>

      {/* Content */}
      <div
        className={cn(
          'grid transition-[grid-template-rows] duration-200 ease-out',
          isExpanded ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'
        )}
      >
        <div className="overflow-hidden">
          <div className="pl-7 space-y-1 text-sm">
            {steps.map((step, index) => (
              <div
                key={`${step.node}-${index}`}
                className={cn(
                  'flex items-start gap-2 py-1',
                  'animate-in fade-in slide-in-from-left-2 duration-300'
                )}
                style={{ animationDelay: `${Math.min(index * 50, 200)}ms` }}
              >
                {/* Status Icon */}
                <div className="relative w-4 h-4 flex items-center justify-center mt-0.5 shrink-0">
                  {step.status === 'running' ? (
                    <>
                      <div className="absolute inset-0 rounded-full bg-amber-500/20 animate-ping" />
                      <Circle className="w-2.5 h-2.5 relative z-10 text-amber-500 fill-amber-500" />
                    </>
                  ) : step.status === 'complete' ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-zinc-400" />
                  ) : (
                    <Circle className="w-2.5 h-2.5 text-zinc-300 dark:text-zinc-600" />
                  )}
                </div>

                {/* Step Name */}
                <span className={cn(
                  'leading-relaxed',
                  step.status === 'running' ? 'text-zinc-800 dark:text-zinc-200' : 'text-zinc-600 dark:text-zinc-500'
                )}>
                  {step.node}
                </span>

                {/* Duration */}
                {step.duration && step.status === 'complete' && (
                  <span className="ml-auto text-xs text-zinc-400 tabular-nums">
                    {step.duration < 1000
                      ? `${step.duration}ms`
                      : `${(step.duration / 1000).toFixed(1)}s`}
                  </span>
                )}
              </div>
            ))}

            {isRunning && steps.length === 0 && (
              <div className="flex items-center gap-2 py-1 text-zinc-500">
                <div className="relative w-4 h-4 flex items-center justify-center">
                  <div className="absolute inset-0 rounded-full bg-amber-500/20 animate-ping" />
                  <Circle className="w-2.5 h-2.5 relative z-10 text-amber-500 fill-amber-500" />
                </div>
                <span>Starting thinking process...</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
