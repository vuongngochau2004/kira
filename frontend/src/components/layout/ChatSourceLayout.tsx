/**
 * Chat Source Layout Component
 * Manages resizable split between chat and source panels
 */

'use client'

import { memo, useState, useCallback, useMemo } from 'react'
import { cn } from '@/lib/utils'
import { PanelResizer } from '@/components/sources/components/PanelResizer'

// ============================================
// Types
// ============================================

export interface ChatSourceLayoutProps {
  children: React.ReactNode
  sourcePanel: React.ReactNode
  defaultSourceWidth?: number
  minSourceWidth?: number
  maxSourceWidth?: number
  className?: string
}

// ============================================
// Constants
// ============================================

const DEFAULT_SOURCE_WIDTH = 400
const MIN_SOURCE_WIDTH = 320
const MAX_SOURCE_WIDTH = 800

// ============================================
// Component
// ============================================

export const ChatSourceLayout = memo<ChatSourceLayoutProps>(
  ({
    children,
    sourcePanel,
    defaultSourceWidth = DEFAULT_SOURCE_WIDTH,
    minSourceWidth = MIN_SOURCE_WIDTH,
    maxSourceWidth = MAX_SOURCE_WIDTH,
    className,
  }) => {
    const [sourceWidth, setSourceWidth] = useState(defaultSourceWidth)
    const [isResizing, setIsResizing] = useState(false)

    // Calculate widths as percentages for better responsiveness
    const totalWidth = 100 // 100%
    const sourceWidthPercent = useMemo(() => {
      return (sourceWidth / window.innerWidth) * 100
    }, [sourceWidth])

    const chatWidth = totalWidth - sourceWidthPercent

    // Handle resize
    const handleResize = useCallback(
      (newWidth: number) => {
        setSourceWidth(newWidth)
      },
      []
    )

    const handleResizeStart = useCallback(() => {
      setIsResizing(true)
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
    }, [])

    const handleResizeEnd = useCallback(() => {
      setIsResizing(false)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }, [])

    return (
      <div
        className={cn(
          'flex h-full overflow-hidden',
          isResizing && 'select-none',
          className
        )}
      >
        {/* Chat Area */}
        <div
          className="flex-1 flex flex-col min-w-0"
          style={{
            width: `calc(100% - ${sourceWidth}px)`,
            transition: isResizing ? 'none' : undefined,
          }}
        >
          {children}
        </div>

        {/* Source Panel with Resizer */}
        <div
          className="flex shrink-0 relative"
          style={{
            width: `${sourceWidth}px`,
            transition: isResizing ? 'none' : 'width 0.3s ease-in-out',
          }}
        >
          {/* Resizer Handle */}
          <PanelResizer
            direction="horizontal"
            size={sourceWidth}
            minSize={minSourceWidth}
            maxSize={maxSourceWidth}
            onResize={handleResize}
            onResizeStart={handleResizeStart}
            onResizeEnd={handleResizeEnd}
            className="-left-3" // Offset to position between panels
          />

          {/* Source Panel Content */}
          <div className="w-full h-full">
            {sourcePanel}
          </div>
        </div>
      </div>
    )
  }
)

ChatSourceLayout.displayName = 'ChatSourceLayout'
