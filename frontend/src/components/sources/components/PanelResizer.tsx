/**
 * Panel Resizer Component
 * Provides draggable handle to resize panel width
 */

import { memo, useState, useCallback, useEffect, useRef } from 'react'
import { GripVertical } from 'lucide-react'
import { cn } from '@/lib/utils'

// ============================================
// Types
// ============================================

export interface ResizerProps {
  onResize: (width: number) => void
  onResizeStart?: () => void
  onResizeEnd?: () => void
  direction?: 'horizontal' | 'vertical'
  resizeFrom?: 'start' | 'end'
  minSize?: number
  maxSize?: number
  size?: number
  className?: string
  disabled?: boolean
}

// ============================================
// Constants
// ============================================

const DEFAULT_MIN_SIZE = 280
const DEFAULT_MAX_SIZE = 800
const RESIZER_THICKNESS = 8
const HANDLE_OFFSET = -4 // Center handle on border

// ============================================
// Component
// ============================================

export const PanelResizer = memo<ResizerProps>(
  ({
    onResize,
    onResizeStart,
    onResizeEnd,
    direction = 'horizontal',
    resizeFrom = 'end',
    minSize = DEFAULT_MIN_SIZE,
    maxSize = DEFAULT_MAX_SIZE,
    size = 340,
    className,
    disabled = false,
  }) => {
    const [isResizing, setIsResizing] = useState(false)
    const startPos = useRef(0)
    const startSize = useRef(size)
    const isResizingRef = useRef(false)
    const resizerRef = useRef<HTMLDivElement>(null)

    const finishResize = useCallback(() => {
      isResizingRef.current = false
      setIsResizing(false)
      document.body.style.userSelect = ''
      document.body.style.cursor = ''
      onResizeEnd?.()
    }, [onResizeEnd])

    // Handle resize start
    const handleMouseDown = useCallback(
      (e: React.MouseEvent) => {
        if (disabled) return

        e.preventDefault()
        isResizingRef.current = true
        setIsResizing(true)
        startSize.current = size

        if (direction === 'horizontal') {
          startPos.current = e.clientX
        } else {
          startPos.current = e.clientY
        }

        onResizeStart?.()

        // Prevent text selection during resize
        document.body.style.userSelect = 'none'
        document.body.style.cursor = direction === 'horizontal' ? 'col-resize' : 'row-resize'

        const handleDocumentMouseMove = (event: MouseEvent) => {
          if (!isResizingRef.current) return

          const delta =
            direction === 'horizontal'
              ? event.clientX - startPos.current
              : event.clientY - startPos.current
          const signedDelta = resizeFrom === 'start' ? -delta : delta
          const newSize = Math.max(
            minSize,
            Math.min(maxSize, startSize.current + signedDelta)
          )

          onResize(newSize)
        }

        const handleDocumentMouseUp = () => {
          document.removeEventListener('mousemove', handleDocumentMouseMove)
          document.removeEventListener('mouseup', handleDocumentMouseUp)
          finishResize()
        }

        document.addEventListener('mousemove', handleDocumentMouseMove)
        document.addEventListener('mouseup', handleDocumentMouseUp)
      },
      [
        disabled,
        size,
        direction,
        resizeFrom,
        minSize,
        maxSize,
        onResize,
        onResizeStart,
        finishResize,
      ]
    )

    // Cleanup on unmount
    useEffect(() => {
      return () => {
        isResizingRef.current = false
        document.body.style.userSelect = ''
        document.body.style.cursor = ''
      }
    }, [])

    // Keyboard accessibility
    const handleKeyDown = useCallback(
      (e: React.KeyboardEvent) => {
        if (disabled) return

        const step = e.shiftKey ? 10 : 1
        let newSize = size

        switch (e.key) {
          case 'ArrowLeft':
          case 'ArrowUp':
            e.preventDefault()
            newSize = size - step
            break
          case 'ArrowRight':
          case 'ArrowDown':
            e.preventDefault()
            newSize = size + step
            break
          default:
            return
        }

        newSize = Math.max(minSize, Math.min(maxSize, newSize))
        onResize(newSize)
      },
      [disabled, size, minSize, maxSize, onResize]
    )

    if (disabled) {
      return null
    }

    return (
      <div
        ref={resizerRef}
        className={cn(
          'absolute z-10 flex items-center justify-center bg-transparent hover:bg-primary/10 transition-colors',
          direction === 'horizontal'
            ? cn(
                'top-0 bottom-0 cursor-col-resize',
                resizeFrom === 'start' ? 'left-0' : 'right-0'
              )
            : 'left-0 right-0 cursor-row-resize',
          isResizing && 'bg-primary/20',
          className
        )}
        style={
          direction === 'horizontal'
            ? { width: RESIZER_THICKNESS }
            : { height: RESIZER_THICKNESS }
        }
        onMouseDown={handleMouseDown}
        onKeyDown={handleKeyDown}
        tabIndex={0}
        role="separator"
        aria-orientation={direction}
        aria-valuenow={size}
        aria-valuemin={minSize}
        aria-valuemax={maxSize}
        aria-label="Resize panel"
      >
        {/* Draggable Handle */}
        <div
          className={cn(
            'flex items-center justify-center rounded bg-background shadow-sm border border-border/50',
            direction === 'horizontal'
              ? 'h-8 w-1.5'
              : 'w-8 h-1.5',
            'hover:bg-primary hover:border-primary transition-colors',
            isResizing && 'bg-primary border-primary'
          )}
          style={
            direction === 'horizontal'
              ? { marginLeft: HANDLE_OFFSET, marginRight: HANDLE_OFFSET }
              : { marginTop: HANDLE_OFFSET, marginBottom: HANDLE_OFFSET }
          }
        >
          <GripVertical
            className={cn(
              'text-muted-foreground',
              direction === 'horizontal' ? 'h-4 w-4' : 'h-4 w-4 rotate-90'
            )}
          />
        </div>

        {/* Size indicator tooltip */}
        {isResizing && (
          <div
            className={cn(
              'absolute bg-primary text-primary-foreground text-xs font-mono px-2 py-1 rounded pointer-events-none',
              direction === 'horizontal'
                ? cn(
                    'top-1/2 -translate-y-1/2',
                    resizeFrom === 'start' ? '-left-16' : '-right-16'
                  )
                : '-bottom-8 left-1/2 -translate-x-1/2'
            )}
          >
            {Math.round(size)}px
          </div>
        )}
      </div>
    )
  }
)

PanelResizer.displayName = 'PanelResizer'
