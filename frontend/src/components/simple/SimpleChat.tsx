'use client'

import { useState, useRef, useEffect, useCallback, memo, useMemo } from 'react'
import { Send, Loader2, X, Paperclip } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ThinkingHierarchy } from '@/components/thinking'
import { ThinkingBlock } from '@/components/streaming/ThinkingBlock'
import { SourceCitation } from '@/components/streaming/SourceCitation'
import { SourcePanel } from '@/components/streaming/SourcePanel'
import { StreamingText } from '@/components/streaming/StreamingText'
import { CitationRichText } from '@/components/streaming/CitationRichText'
import { CitationPanel, type CitationSource, type VerificationStats } from '@/components/streaming/CitationPanel'
import { useSourcesStore } from '@/lib/stores/sources-store'
import { KIRAWelcome } from '@/components/common/KiraLogo'
import type { ThinkingHierarchy as ThinkingHierarchyType } from '@/types/thinking'

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
  thinking?: ThinkingStep[]  // Legacy, for backward compatibility
  thinkingHierarchy?: ThinkingHierarchyType  // NEW structured thinking
  isStreaming?: boolean
  streamingState?: 'connecting' | 'routing' | 'retrieving' | 'generating' | 'complete' | 'error'
  citation_verification?: VerificationStats
  use_new_citation_format?: boolean  // Use [source:chunk_id] format
  isOptimistic?: boolean  // NEW: Mark optimistic messages for UI indication
  rejection_detected?: boolean  // ✅ NEW: Explicit backend rejection signal
  rejection_reasoning?: string  // ✅ NEW: LLM's explanation for rejection (Vietnamese)
}

interface SimpleChatProps {
  messages: Message[]
  optimisticMessages?: Message[]  // NEW: Optimistic messages for first-message UX
  isLoading: boolean
  onSendMessage: (content: string) => void
  onClearChat: () => void
  error?: string | null
  className?: string
  isNewChat?: boolean
  isOptimistic?: boolean  // NEW: Show optimistic state indicator
  retryMessage?: () => void  // NEW: Retry failed message
  isRetryable?: boolean  // NEW: Show retry button
  errorType?: string  // NEW: Error type for custom handling
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
  const isStreaming = message.isStreaming ?? isLoading

  return (
    <>
      {/* Thinking Block - Use new ThinkingHierarchy if available, fallback to legacy */}
      {message.thinkingHierarchy ? (
        <ThinkingHierarchy hierarchy={message.thinkingHierarchy} />
      ) : (
        <ThinkingBlock
          steps={message.thinking || []}
          isLoading={isLoading}
          streamingState={message.streamingState}
        />
      )}

      {/* Content */}
      <div className="text-base py-2 text-foreground">
        {message.use_new_citation_format ? (
          <CitationRichText
            content={message.content || ''}
            isStreaming={isStreaming}
            className="text-[15px] md:text-base leading-relaxed"
            citations={message.sources as unknown as CitationSource[]}
            onCitationClick={(chunkId, citation) => {
              // Handle citation click - will open CitationPanel
              onCitationClick?.(parseInt(chunkId, 36), message.sources?.[0] || citation as any)
            }}
          />
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
      message.role === 'user' ? 'justify-end' : 'justify-start',
      // NEW: Optimistic indicator - slight opacity for optimistic messages
      message.isOptimistic && 'opacity-70'
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
      {message.role === 'assistant' && message.sources && message.sources.length > 0 && !message.use_new_citation_format && !message.rejection_detected && (
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

      {/* Citation Button - New format */}
      {message.role === 'assistant' && message.use_new_citation_format && message.sources && message.sources.length > 0 && !message.rejection_detected && (
        <div className="mt-2">
          <button
            onClick={() => {
              // Open citation panel - will be handled by parent
              onCitationClick(0, message.sources![0])
            }}
            className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium bg-muted hover:bg-muted/70 transition-colors"
          >
            <span>📚 {message.sources.length} nguồn</span>
            {message.citation_verification && (
              <span className="text-green-600 dark:text-green-400">
                ({message.citation_verification.verified}/{message.citation_verification.total} verified)
              </span>
            )}
          </button>
        </div>
      )}

      {/* ✅ Rejection Indicator - NEW */}
      {message.role === 'assistant' && message.rejection_detected && (
        <div className="mt-2 text-xs text-muted-foreground italic flex items-center gap-1.5">
          <span>ℹ️</span>
          <span>{message.rejection_reasoning || "Không tìm thấy thông tin trong tài liệu"}</span>
        </div>
      )}
    </div>
  </div>
))
MessageRow.displayName = 'MessageRow'

// ==================== Main Component ====================

export function SimpleChat({
  messages,
  optimisticMessages,
  isLoading,
  onSendMessage,
  onClearChat,
  error,
  className,
  isNewChat = true,
  isOptimistic = false,
  retryMessage,
  isRetryable = false,
  errorType
}: SimpleChatProps) {
  const store = useSourcesStore()
  const [input, setInput] = useState('')
  const [sourcePanelOpen, setSourcePanelOpen] = useState(false)
  const [citationPanelOpen, setCitationPanelOpen] = useState(false)
  const [activeCitationChunkId, setActiveCitationChunkId] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)

  // NEW: Merge optimistic messages with real messages for display
  const displayMessages = useMemo(() => {
    if (!optimisticMessages || optimisticMessages.length === 0) {
      return messages
    }

    // Deduplicate by ID - real messages take priority over optimistic
    const messageMap = new Map<string, Message>()

    // Add optimistic messages first (they'll be overwritten by real ones)
    optimisticMessages.forEach(msg => {
      messageMap.set(msg.id, msg)
    })

    // Add real messages - they OVERWRITE optimistic versions with same ID
    messages.forEach(msg => {
      messageMap.set(msg.id, msg)
    })

    const merged = Array.from(messageMap.values()).sort(
      (a, b) => a.timestamp.getTime() - b.timestamp.getTime()
    )

    // DEBUG: Log assistant messages with thinking hierarchy
    const assistantMsgs = merged.filter(m => m.role === 'assistant' && m.thinkingHierarchy)
    console.log('[DEBUG SimpleChat] displayMessages:', {
      total: merged.length,
      withThinking: assistantMsgs.length,
      assistantMsgs: assistantMsgs.map(m => ({
        id: m.id,
        hasThinking: !!m.thinkingHierarchy,
        status: m.thinkingHierarchy?.status,
        execution: m.thinkingHierarchy?.execution?.length,
        isOptimistic: m.isOptimistic,
      }))
    })

    return merged
  }, [messages, optimisticMessages])

  // Welcome screen state
  const [welcomeVisible, setWelcomeVisible] = useState(isNewChat)
  const [welcomeExiting, setWelcomeExiting] = useState(false)

  // Get latest assistant message with citations
  const latestAssistantMessage = messages.filter(m => m.role === 'assistant').pop()
  const hasNewCitationFormat = latestAssistantMessage?.use_new_citation_format
  const citationSources = hasNewCitationFormat ? (latestAssistantMessage?.sources as unknown as CitationSource[]) : undefined
  const verificationStats = latestAssistantMessage?.citation_verification

  // ==================== Effects ====================

  /**
   * Auto-scroll to bottom on new messages
   * Scrolls smoothly when new messages arrive or content updates during streaming
   */
  const prevMessagesLengthRef = useRef<number>(0)
  const isUserScrolledRef = useRef<boolean>(false)

  useEffect(() => {
    const container = messagesContainerRef.current
    if (!container) return

    // Detect if user manually scrolled up
    const handleScroll = () => {
      const isAtBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 100
      isUserScrolledRef.current = !isAtBottom
    }

    container.addEventListener('scroll', handleScroll)
    return () => container.removeEventListener('scroll', handleScroll)
  }, [])

  useEffect(() => {
    const container = messagesContainerRef.current
    if (!container) return

    // Scroll if: new message arrived OR (loading and user hasn't scrolled up)
    const isNewMessage = messages.length > prevMessagesLengthRef.current
    const shouldAutoScroll = isNewMessage || (isLoading && !isUserScrolledRef.current)

    if (shouldAutoScroll) {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: isNewMessage ? 'smooth' : 'auto'
      })
    }

    prevMessagesLengthRef.current = messages.length
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

    // Focus back to input with minimal delay
    requestAnimationFrame(() => {
      textareaRef.current?.focus()
    })
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
    // Check if message uses new citation format
    const message = messages.find(m => m.sources?.some(s => s.id === source.id))
    const useNewFormat = message?.use_new_citation_format

    if (useNewFormat) {
      // Use new CitationPanel
      const citation = (allSources || message?.sources || [])[citationIndex] as unknown as CitationSource
      setActiveCitationChunkId(citation?.chunk_id || null)
      setCitationPanelOpen(true)
    } else {
      // Use old SourcePanel
      const sources = allSources || messages.find(m => m.id === source.id)?.sources || []
      store.setSources(sources)
      store.setIsOpen(true)
      const targetId = source.chunk_id || source.id || `source-${citationIndex}`
      store.setActiveSourceId(targetId)
    }
  }, [store, messages])

  // ==================== Render ====================

  // Get visible messages (merge optimistic with real)
  const visibleMessages = displayMessages
  return (
    <div className={cn('flex flex-col h-full bg-background min-h-0', className)}>
      {/* Messages Area */}
      <div ref={messagesContainerRef} className="flex-1 overflow-y-auto min-h-0 scroll-smooth">
        <div className="max-w-3xl mx-auto px-4 py-6">
          {welcomeVisible ? (
            <div
              className={cn(
                'transition-opacity duration-300 ease-in-out',
                welcomeExiting ? 'opacity-0' : 'opacity-100'
              )}
            >
              <KIRAWelcome className="min-h-full" variant="gradient" />
            </div>
          ) : (
            <>
              {visibleMessages.map((message, index) => (
                <MessageRow
                  key={message.id}
                  message={message}
                  isLoading={isLoading}
                  isLast={index === visibleMessages.length - 1}
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
            <div className="flex gap-2">
              {isRetryable && retryMessage && (
                <button onClick={retryMessage} className="text-xs underline hover:underline">
                  Thử lại
                </button>
              )}
              <button onClick={() => window.location.reload()} className="text-xs underline hover:underline">
                Tải lại
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Input Area - Modern Floating Capsule */}
      <div className="shrink-0 bg-background pb-4">
        <div className="max-w-3xl mx-auto px-4">
          <form onSubmit={handleSubmit} className="relative">
            {/* Main Input Container - Elevated capsule with shadow */}
            <div
              className={cn(
                'flex items-center gap-2 p-2',
                'bg-card/80 backdrop-blur-sm',
                'border border-border/50 rounded-2xl',
                'shadow-lg shadow-primary/5',
                'transition-all duration-200 ease-out',
                // Focus state glow effect
                'hover:border-primary/20',
                'focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary/40'
              )}
            >
              {/* Attach Button - Integrated into capsule */}
              <button
                type="button"
                onClick={handleFileAttach}
                className={cn(
                  'shrink-0 h-10 w-10 rounded-xl flex items-center justify-center',
                  'text-muted-foreground transition-all duration-150',
                  'hover:bg-primary/10 hover:text-primary hover:scale-105',
                  'active:scale-95'
                )}
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

              {/* Text Input - Clean, minimal */}
              <div className="flex-1 relative">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Hỏi tôi bất cứ điều gì..."
                  rows={1}
                  className={cn(
                    'w-full resize-none bg-transparent border-0',
                    'px-3 py-2.5 pr-10 text-sm placeholder:text-muted-foreground/60',
                    'focus:outline-none focus:ring-0',
                    'disabled:opacity-50 disabled:cursor-not-allowed',
                    'max-h-32 overflow-y-auto custom-scrollbar'
                  )}
                  disabled={isLoading}
                  style={{ minHeight: '40px' }}
                />
                {/* Clear Button - Shows when empty and has messages */}
                {messages.length > 0 && input.length === 0 && (
                  <button
                    type="button"
                    onClick={onClearChat}
                    className={cn(
                      'absolute right-2 top-1/2 -translate-y-1/2',
                      'text-muted-foreground/60 hover:text-muted-foreground',
                      'transition-colors p-1 rounded-md',
                      'hover:bg-muted/50'
                    )}
                    title="Xoá cuộc trò chuyện"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* Send Button - Prominent primary action */}
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className={cn(
                  'shrink-0 h-10 px-4 rounded-xl flex items-center justify-center gap-2',
                  'bg-primary text-primary-foreground font-medium text-sm',
                  'shadow-md shadow-primary/20',
                  'transition-all duration-150 ease-out',
                  // Enabled states
                  'hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/30 hover:scale-105',
                  'active:scale-95',
                  // Disabled states
                  'disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100 disabled:shadow-md'
                )}
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>

            {/* Optional: Helper text below input */}
            <div className="mt-2 flex items-center justify-center gap-4 text-xs text-muted-foreground/60">
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 rounded bg-muted/80 font-mono">Enter</kbd> để gửi
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 rounded bg-muted/80 font-mono">Shift + Enter</kbd> để xuống dòng
              </span>
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

      {/* Citation Panel - New format */}
      {citationSources && (
        <CitationPanel
          citations={citationSources}
          isOpen={citationPanelOpen}
          onClose={() => setCitationPanelOpen(false)}
          verificationStats={verificationStats}
          activeChunkId={activeCitationChunkId}
        />
      )}
    </div>
  )
}
