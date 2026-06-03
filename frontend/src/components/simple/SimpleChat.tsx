'use client'

import { useState, useRef, useEffect, useCallback, memo } from 'react'
import { Send, Loader2, X, Paperclip } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ThinkingBlock } from '@/components/streaming/ThinkingBlock'
import { SourceCitation } from '@/components/streaming/SourceCitation'
import { SourcePanel } from '@/components/streaming/SourcePanel'
import { StreamingText } from '@/components/streaming/StreamingText'
import { useSourcesStore } from '@/lib/stores/sources-store'
import { KiraWelcome } from '@/components/common/KiraLogo'

// ==================== Types ====================

export interface ThinkingStep {
  node: string
  status: 'pending' | 'running' | 'complete'
  duration?: number
  timestamp?: number
}

export interface SourceChunk {
  id: string
  chunk_id?: string
  content: string
  score: number
  document_id?: string
  chunk_index?: number
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sources?: SourceChunk[]
  thinking?: ThinkingStep[]
  isStreaming?: boolean
  streamingState?: 'connecting' | 'routing' | 'retrieving' | 'generating' | 'complete' | 'error'
}

interface SimpleChatProps {
  messages: Message[]
  isLoading: boolean
  onSendMessage: (content: string) => void
  onClearChat: () => void
  error?: string | null
  className?: string
  isNewChat?: boolean
}

// ==================== Memoized Components ====================

/**
 * User message component - memoized to prevent unnecessary re-renders
 */
const UserMessage = memo(({ content }: { content: string }) => (
  <div className="bg-muted/60 text-foreground px-5 py-3 rounded-3xl">
    <p className="whitespace-pre-wrap break-words leading-relaxed">
      {content}
    </p>
  </div>
))
UserMessage.displayName = 'UserMessage'

/**
 * Assistant message component with streaming support
 */
const AssistantMessage = memo((
  { message, isLoading, onCitationClick }: {
    message: Message
    isLoading: boolean
    onCitationClick: (index: number, source: SourceChunk) => void
  }
) => {
  const showLoader = !message.content && isLoading
  const isStreaming = message.isStreaming ?? isLoading

  return (
    <>
      {/* Thinking Block */}
      <ThinkingBlock
        steps={message.thinking || []}
        isLoading={isLoading}
        streamingState={message.streamingState}
      />

      {/* Content */}
      <div className="text-base py-2 text-foreground">
        {showLoader ? (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">Đang phản hồi...</span>
          </div>
        ) : (
          <StreamingText
            content={message.content || ''}
            isStreaming={isStreaming}
            className="text-[15px] md:text-base leading-relaxed"
            sources={message.sources}
            onCitationClick={onCitationClick}
          />
        )}
      </div>
    </>
  )
})
AssistantMessage.displayName = 'AssistantMessage'

/**
 * Message row component
 */
const MessageRow = memo((
  { message, isLoading, isLast, onCitationClick }: {
    message: Message
    isLoading: boolean
    isLast: boolean
    onCitationClick: (index: number, source: SourceChunk) => void
  }
) => (
  <div
    className={cn(
      'flex gap-3 mb-6',
      message.role === 'user' ? 'justify-end' : 'justify-start'
    )}
  >
    <div className={cn(
      'max-w-[85%]',
      message.role === 'user' ? 'flex flex-col items-end' : 'flex flex-col w-full max-w-full'
    )}>
      {message.role === 'assistant' ? (
        <AssistantMessage
          message={message}
          isLoading={isLoading && isLast}
          onCitationClick={onCitationClick}
        />
      ) : (
        <UserMessage content={message.content} />
      )}

      {/* Source Citation */}
      {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
        <div className="mt-2">
          <SourceCitation
            sources={message.sources}
            onClick={() => {
              // Click handler will be provided by parent
              onCitationClick(0, message.sources![0])
            }}
          />
        </div>
      )}
    </div>
  </div>
))
MessageRow.displayName = 'MessageRow'

// ==================== Main Component ====================

export function SimpleChat({
  messages,
  isLoading,
  onSendMessage,
  onClearChat,
  error,
  className,
  isNewChat = true
}: SimpleChatProps) {
  const store = useSourcesStore()
  const [input, setInput] = useState('')
  const [sourcePanelOpen, setSourcePanelOpen] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Welcome screen state
  const [welcomeVisible, setWelcomeVisible] = useState(isNewChat)
  const [welcomeExiting, setWelcomeExiting] = useState(false)

  // ==================== Effects ====================

  /**
   * Auto-scroll to bottom on new messages
   */
  useEffect(() => {
    if (isLoading) {
      bottomRef.current?.scrollIntoView({ behavior: 'auto' })
    } else {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, isLoading])

  /**
   * Handle welcome screen fade-out
   */
  useEffect(() => {
    if (messages.length > 0 && welcomeVisible) {
      setWelcomeExiting(true)
      const timer = setTimeout(() => {
        setWelcomeVisible(false)
        setWelcomeExiting(false)
      }, 300)
      return () => clearTimeout(timer)
    }
  }, [messages.length, welcomeVisible])

  // ==================== Handlers ====================

  /**
   * Handle form submission
   */
  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    onSendMessage(input.trim())
    setInput('')
    setTimeout(() => textareaRef.current?.focus(), 100)
  }, [input, isLoading, onSendMessage])

  /**
   * Handle keyboard events
   */
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }, [handleSubmit])

  /**
   * Handle file attachment
   */
  const handleFileAttach = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  /**
   * Handle citation click - memoized to prevent re-renders
   */
  const handleCitationClick = useCallback((citationIndex: number, source: SourceChunk, allSources?: SourceChunk[]) => {
    const sources = allSources || messages.find(m => m.id === source.id)?.sources || []
    store.setSources(sources)
    store.setIsOpen(true)
    const targetId = source.chunk_id || source.id || `source-${citationIndex}`
    store.setActiveSourceId(targetId)
  }, [store, messages])

  // ==================== Render ====================

  return (
    <div className={cn('flex flex-col h-full bg-background min-h-0', className)}>
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto min-h-0">
        <div className="max-w-3xl mx-auto px-4 py-6">
          {welcomeVisible ? (
            <div
              className={cn(
                'transition-opacity duration-300 ease-in-out',
                welcomeExiting ? 'opacity-0' : 'opacity-100'
              )}
            >
              <KiraWelcome className="min-h-full" variant="gradient" />
            </div>
          ) : (
            <>
              {messages.map((message, index) => (
                <MessageRow
                  key={message.id}
                  message={message}
                  isLoading={isLoading}
                  isLast={index === messages.length - 1}
                  onCitationClick={(idx, src) => handleCitationClick(idx, src, message.sources)}
                />
              ))}

              <div ref={bottomRef} />
            </>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="max-w-3xl mx-auto px-4 pb-2">
          <div className="bg-destructive/10 text-destructive text-sm px-4 py-3 rounded-xl flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => window.location.reload()} className="text-xs underline hover:underline">
              Thử lại
            </button>
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="shrink-0 bg-background">
        <div className="max-w-3xl mx-auto p-4">
          <form onSubmit={handleSubmit} className="relative">
            <div className="flex items-end gap-2">
              {/* Attach Button */}
              <button
                type="button"
                onClick={handleFileAttach}
                className="shrink-0 h-10 w-10 rounded-full flex items-center justify-center text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                title="Đính kèm tài liệu"
              >
                <Paperclip className="w-5 h-5" />
              </button>
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".pdf,.docx,.doc,.txt,.png,.jpg,.jpeg,.tiff"
              />

              {/* Text Input */}
              <div className="flex-1 relative">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Nhập tin nhắn..."
                  rows={1}
                  className={cn(
                    'w-full resize-none rounded-full border border-input bg-background',
                    'px-4 py-2.5 pr-10 text-sm placeholder:text-muted-foreground',
                    'focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary',
                    'disabled:opacity-50 disabled:cursor-not-allowed',
                    'max-h-32 overflow-y-auto'
                  )}
                  disabled={isLoading}
                  style={{ minHeight: '42px' }}
                />
                {messages.length > 0 && input.length === 0 && (
                  <button
                    type="button"
                    onClick={onClearChat}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors p-1"
                    title="Xoá cuộc trò chuyện"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* Send Button */}
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className={cn(
                  'shrink-0 h-10 w-10 rounded-full flex items-center justify-center',
                  'bg-primary text-primary-foreground',
                  'hover:bg-primary/90 transition-colors',
                  'disabled:opacity-40 disabled:cursor-not-allowed'
                )}
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Source Panel - Mobile/Tablet only */}
      <SourcePanel
        sources={store.sources.map((s) => ({
          id: s.id,
          content: s.snippet,
          score: s.score,
          document_id: s.document_id || undefined,
          chunk_index: s.page !== undefined ? s.page - 1 : undefined,
        }))}
        isOpen={store.isOpen || sourcePanelOpen}
        onClose={() => {
          store.setIsOpen(false)
          setSourcePanelOpen(false)
        }}
        activeSourceId={store.activeSourceId}
        className="lg:hidden"
      />
    </div>
  )
}
