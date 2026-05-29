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

  const displaySteps = useMemo(() => {
    if (steps.length > 0) return steps
    if (!isLoading) {
      return [
        {
          node: 'Thinking process completed',
          status: 'complete' as const,
        },
      ]
    }
    return []
  }, [steps, isLoading])

  const isRunning = useMemo(
    () => displaySteps.some((s) => s.status === 'running') || isLoading,
    [displaySteps, isLoading]
  )

  const isComplete = useMemo(
    () => displaySteps.length > 0 && displaySteps.every((s) => s.status === 'complete'),
    [displaySteps]
  )

  useEffect(() => {
    if (isRunning && !isExpanded) {
      setIsExpanded(true)
    }
  }, [isRunning])

  const handleToggle = () => setIsExpanded(!isExpanded)

  if (displaySteps.length === 0 && !isLoading) return null

  return (
    <div className={cn('py-2 border-0 shadow-none', className)}>
      {/* Header */}
      <button
        onClick={handleToggle}
        className="flex items-center gap-2 text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors border-0 outline-none"
      >
        {/* Sparkles icon without ping animation */}
        <div className="relative w-4 h-4 flex items-center justify-center border-0">
          <Sparkles className={cn(
            'w-3.5 h-3.5 relative z-10 border-0',
            isRunning ? 'text-zinc-650 dark:text-zinc-300' : 'text-zinc-400'
          )} />
        </div>

        <span className="text-sm font-medium border-0">Thinking</span>

        <ChevronDown
          className={cn(
            'w-4 h-4 transition-transform duration-200 border-0',
            !isExpanded && '-rotate-90'
          )}
        />
      </button>

      {/* Content */}
      <div
        className={cn(
          'grid transition-[grid-template-rows] duration-200 ease-out border-0',
          isExpanded ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'
        )}
      >
        <div className="overflow-hidden border-0">
          <div className="pl-7 space-y-3 text-sm pt-2 border-0">
            {displaySteps.map((step, index) => {
              // Parse the hierarchical content
              const lines = step.node.split('\n')
              const header = lines[0] || 'Agent'
              const details = lines.slice(1).join('\n')

              return (
                <StepItem
                  key={`${step.node}-${index}`}
                  header={header}
                  details={details}
                  status={step.status}
                  duration={step.duration}
                  index={index}
                />
              )
            })}

            {isRunning && displaySteps.length === 0 && (
              <div className="flex items-center gap-2 py-1 text-zinc-500 border-0">
                <div className="relative w-4 h-4 flex items-center justify-center border-0">
                  <Circle className="w-2.5 h-2.5 relative z-10 text-zinc-400 fill-zinc-400 dark:text-zinc-500 dark:fill-zinc-500 border-0" />
                </div>
                <span className="border-0">
                  Starting thinking process
                  <span className="inline-flex ml-0.5 text-zinc-500 font-bold">
                    <span className="animate-[pulse_1.2s_infinite_0ms]">.</span>
                    <span className="animate-[pulse_1.2s_infinite_200ms]">.</span>
                    <span className="animate-[pulse_1.2s_infinite_400ms]">.</span>
                  </span>
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

interface StepItemProps {
  header: string
  details: string
  status: 'pending' | 'running' | 'complete'
  duration?: number
  index: number
}

function StepItem({ header, details, status, duration, index }: StepItemProps) {
  const [isOpen, setIsOpen] = useState(true)

  // Auto-expand on running, collapse on complete if preferred. Let's default open.
  useEffect(() => {
    if (status === 'running') {
      setIsOpen(true)
    }
  }, [status])

  return (
    <div
      className={cn(
        'overflow-hidden border-0 shadow-none'
      )}
    >
      {/* Header section with toggle */}
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between py-1.5 cursor-pointer select-none text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors border-0 outline-none"
      >
        <div className="flex items-center gap-2 flex-1 min-w-0 border-0">
          {/* Status Icon */}
          <div className="relative w-4 h-4 flex items-center justify-center shrink-0 border-0">
            {status === 'running' ? (
              <Circle className="w-2 h-2 text-zinc-400 fill-zinc-400 dark:text-zinc-500 dark:fill-zinc-500 border-0" />
            ) : status === 'complete' ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-zinc-400 border-0" />
            ) : (
              <Circle className="w-2 h-2 text-zinc-355 dark:text-zinc-600 border-0" />
            )}
          </div>

          <span
            className={cn(
              'font-semibold text-sm truncate border-0',
              status === 'running' ? 'text-zinc-800 dark:text-zinc-200' : 'text-zinc-600 dark:text-zinc-500'
            )}
          >
            {header}
            {status === 'running' && (
              <span className="inline-flex ml-0.5 text-zinc-500 font-bold">
                <span className="animate-[pulse_1.2s_infinite_0ms]">.</span>
                <span className="animate-[pulse_1.2s_infinite_200ms]">.</span>
                <span className="animate-[pulse_1.2s_infinite_400ms]">.</span>
              </span>
            )}
          </span>
        </div>

        <div className="flex items-center gap-2 shrink-0 border-0">
          {duration && status === 'complete' && (
            <span className="text-xs text-zinc-400 tabular-nums border-0">
              {duration < 1000 ? `${duration}ms` : `${(duration / 1000).toFixed(1)}s`}
            </span>
          )}
          <div className="text-zinc-400 hover:text-zinc-650 dark:hover:text-zinc-300 p-0.5 rounded-md hover:bg-zinc-100/50 dark:hover:bg-zinc-850/50 transition-all border-0">
            {isOpen ? <ChevronDown className="w-3.5 h-3.5 border-0" /> : <ChevronRight className="w-3.5 h-3.5 border-0" />}
          </div>
        </div>
      </div>

      {/* Details container */}
      {details && (
        <div
          className={cn(
            'grid transition-[grid-template-rows] duration-200 ease-out border-0 shadow-none',
            isOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'
          )}
        >
          <div className="overflow-hidden border-0">
            <div className="pl-6 py-2 text-zinc-550 dark:text-zinc-400 font-normal leading-relaxed whitespace-pre-wrap break-words border-0 border-none outline-none text-[13px] shadow-none">
              {details}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
