'use client'

import { memo, useEffect, useState, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn } from '@/lib/utils'

interface SourceChunk {
  id: string
  chunk_id?: string
  content: string
  score: number
  document_id?: string
  chunk_index?: number
}

interface StreamingTextProps {
  content: string
  isStreaming?: boolean
  className?: string
  sources?: SourceChunk[]
  onCitationClick?: (index: number, source: SourceChunk) => void
}

// Preprocess content for citation links
const preprocessContent = (content: string) => {
  if (!content) return ''
  return content.replace(/(?<!\[)\[(\d+)\](?!\]|\()/g, '[$1](#source-$1)')
}

// Streaming component: plain text with smooth cursor animation
const StreamingContent = memo(({ content }: { content: string }) => {
  const [visibleContent, setVisibleContent] = useState(content)
  const [cursorVisible, setCursorVisible] = useState(true)
  const prevContentRef = useRef(content)

  // Smooth cursor blink
  useEffect(() => {
    const interval = setInterval(() => {
      setCursorVisible((v) => !v)
    }, 530) // Slightly offset from standard blink for organic feel
    return () => clearInterval(interval)
  }, [])

  // Update visible content when streaming
  useEffect(() => {
    if (content !== prevContentRef.current) {
      // Small delay for smoother appearance
      const timer = setTimeout(() => {
        setVisibleContent(content)
        prevContentRef.current = content
      }, 10)
      return () => clearTimeout(timer)
    }
  }, [content])

  return (
    <div className={cn(
      'whitespace-pre-wrap leading-relaxed text-foreground',
      'text-[15px] md:text-base'
    )}>
      {visibleContent}
      <span
        className={cn(
          'inline-block w-0.5 h-4 bg-primary ml-0.5 align-middle',
          'transition-opacity duration-200',
          cursorVisible ? 'opacity-100' : 'opacity-0'
        )}
        style={{
          animation: 'cursor-blink 1s step-end infinite',
        }}
      />
      <style jsx>{`
        @keyframes cursor-blink {
          0%, 49% { opacity: 1; }
          50%, 100% { opacity: 0; }
        }
      `}</style>
    </div>
  )
})
StreamingContent.displayName = 'StreamingContent'

// Static component: ReactMarkdown for rich formatting
const StaticContent = memo(({ content, sources, onCitationClick }: {
  content: string
  sources?: SourceChunk[]
  onCitationClick?: (index: number, source: SourceChunk) => void
}) => (
  <ReactMarkdown
    remarkPlugins={[remarkGfm]}
    components={{
      p: ({ children }) => <p className="mb-4 last:mb-0 leading-relaxed">{children}</p>,
      strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
      ul: ({ children }) => <ul className="list-disc pl-5 mb-4 space-y-1">{children}</ul>,
      ol: ({ children }) => <ol className="list-decimal pl-5 mb-4 space-y-1">{children}</ol>,
      li: ({ children }) => <li className="leading-relaxed">{children}</li>,
      h1: ({ children }) => <h1 className="text-2xl font-bold mt-6 mb-3 text-foreground">{children}</h1>,
      h2: ({ children }) => <h2 className="text-xl font-bold mt-5 mb-2.5 text-foreground">{children}</h2>,
      h3: ({ children }) => <h3 className="text-lg font-semibold mt-4 mb-2 text-foreground">{children}</h3>,
      a: ({ href, children }) => {
        if (href && href.startsWith('#source-')) {
          const citationIndex = parseInt(href.replace('#source-', ''), 10) - 1
          if (sources && sources.length > citationIndex && onCitationClick) {
            return (
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  onCitationClick(citationIndex, sources[citationIndex])
                }}
                className={cn(
                  "inline-flex items-center justify-center rounded px-1.5 py-0.5 mx-0.5",
                  "bg-primary/15 hover:bg-primary/25 active:bg-primary/35 text-primary",
                  "text-xs font-semibold font-mono leading-none transition-colors duration-150",
                  "border border-primary/20 hover:border-primary/30 align-middle shrink-0",
                  "cursor-pointer"
                )}
                style={{ verticalAlign: 'baseline', position: 'relative', top: '-1px' }}
                title="Xem nguồn"
              >
                {children}
              </button>
            )
          }
        }
        return (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:underline"
          >
            {children}
          </a>
        )
      },
      code: ({ className, children }) => {
        const match = /language-(\w+)/.exec(className || '')
        return match ? (
          <pre className="bg-muted p-4 rounded-xl overflow-x-auto text-sm my-4 font-mono">
            <code>{children}</code>
          </pre>
        ) : (
          <code className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono">{children}</code>
        )
      }
    }}
  >
    {preprocessContent(content)}
  </ReactMarkdown>
))
StaticContent.displayName = 'StaticContent'

/**
 * StreamingText component that switches between plain text and ReactMarkdown
 * - During streaming: plain text with smooth cursor animation (real-time updates)
 * - When complete: ReactMarkdown with rich formatting
 */
export function StreamingText({
  content,
  isStreaming = false,
  className,
  sources,
  onCitationClick
}: StreamingTextProps) {
  return (
    <div className={cn('prose dark:prose-invert max-w-none', className)}>
      {isStreaming ? (
        <StreamingContent content={content} />
      ) : (
        <StaticContent
          content={content}
          sources={sources}
          onCitationClick={onCitationClick}
        />
      )}
    </div>
  )
}
