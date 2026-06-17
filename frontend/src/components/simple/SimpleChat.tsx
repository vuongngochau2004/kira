'use client'

import { useState, useRef, useEffect, useCallback, memo, useMemo } from 'react'
import { Check, Copy, Download, FileText, Paperclip, Pencil, Send, Square, X } from 'lucide-react'
import { cn } from '@/lib/utils'

import { SourceCitation } from '@/components/streaming/SourceCitation'
import { SourcePanel } from '@/components/streaming/SourcePanel'
import { StreamingText } from '@/components/streaming/StreamingText'
import { CitationRichText } from '@/components/streaming/CitationRichText'
import { CitationPanel, type CitationSource, type VerificationStats } from '@/components/streaming/CitationPanel'
import { useSourcesStore } from '@/lib/stores/sources-store'
import { KIRAWelcome } from '@/components/common/KiraLogo'
import type { Attachment } from '@/lib/streaming'

// ==================== Types ====================


export interface SourceChunk {
  id: string
  chunk_id?: string
  content: string
  score: number
  document_id?: string
  chunk_index?: number
  title?: string
  source?: string
  snippet?: string
  page_number?: number
  grounding_score?: number
  type?: 'pdf' | 'docx' | 'web'
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sources?: SourceChunk[]
  attachments?: Attachment[]
  isStreaming?: boolean
  streamingState?: 'connecting' | 'routing' | 'retrieving' | 'generating' | 'complete' | 'error'
  citation_verification?: VerificationStats
  use_new_citation_format?: boolean  // Use [source:chunk_id] format
  isOptimistic?: boolean  // NEW: Mark optimistic messages for UI indication
}

interface SimpleChatProps {
  messages: Message[]
  optimisticMessages?: Message[]  // NEW: Optimistic messages for first-message UX
  isLoading: boolean
  onSendMessage: (content: string) => void
  onStopGenerating?: () => void
  onClearChat: () => void
  error?: string | null
  className?: string
  activeConversationId?: string | null
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

const SPINNER_WORDS = [
  'Thinking...',
  'Processing...',
  'Reading...',
  'Checking...',
  'Composing...',
]

const ThinkingWordSpinner = memo(() => {
  const [wordIndex, setWordIndex] = useState(0)

  useEffect(() => {
    const interval = window.setInterval(() => {
      setWordIndex((current) => (current + 1) % SPINNER_WORDS.length)
    }, 1100)

    return () => window.clearInterval(interval)
  }, [])

  return (
    <div
      aria-label="Đang tạo câu trả lời"
      className="mb-2 text-xs font-medium text-muted-foreground/70 animate-pulse"
    >
      {SPINNER_WORDS[wordIndex]}
    </div>
  )
})
ThinkingWordSpinner.displayName = 'ThinkingWordSpinner'

const MessageAttachments = memo(({ attachments }: { attachments?: Attachment[] }) => {
  if (!attachments || attachments.length === 0) return null

  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {attachments.map((attachment) => (
        <a
          key={attachment.id}
          href={attachment.download_url}
          download={attachment.filename}
          target="_blank"
          rel="noreferrer"
          className="inline-flex max-w-full items-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
          title={attachment.filename}
        >
          <FileText className="h-4 w-4 shrink-0 text-primary" />
          <span className="truncate">{attachment.filename}</span>
          <Download className="h-4 w-4 shrink-0 text-muted-foreground" />
        </a>
      ))}
    </div>
  )
})
MessageAttachments.displayName = 'MessageAttachments'

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
      {/* Content */}
      <div className="text-base py-2 text-foreground">
        {isStreaming && <ThinkingWordSpinner />}
        {message.use_new_citation_format ? (
          <CitationRichText
            content={message.content || ''}
            isStreaming={isStreaming}
            className="text-[15px] md:text-base leading-relaxed"
            citations={message.sources as unknown as CitationSource[]}
            onCitationClick={(chunkId, citation) => {
              const citationIndex = message.sources?.findIndex((source) => {
                const sourceId = source.chunk_id || source.id
                return sourceId === chunkId
              }) ?? -1

              onCitationClick?.(
                citationIndex >= 0 ? citationIndex : 0,
                (citation || message.sources?.[0]) as SourceChunk
              )
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
  { message, isLoading, isLast, copiedMessageId, onCitationClick, onCopyMessage, onEditMessage }: {
    message: Message
    isLoading: boolean
    isLast: boolean
    copiedMessageId: string | null
    onCitationClick: (index: number, source: SourceChunk) => void
    onCopyMessage: (message: Message) => void
    onEditMessage: (message: Message) => void
  }
) => (
  <div
    data-message-id={message.id}
    data-message-role={message.role}
    className={cn(
      'group/message flex gap-3 mb-6',
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
      {message.role === 'assistant' && message.sources && message.sources.length > 0 && !message.use_new_citation_format && (
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
      {message.role === 'assistant' && message.use_new_citation_format && message.sources && message.sources.length > 0 && (
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

      {message.role === 'assistant' && (
        <MessageAttachments attachments={message.attachments} />
      )}

      <div
        className={cn(
          'mt-2 flex items-center gap-1 text-muted-foreground opacity-0 transition-opacity duration-150 group-hover/message:opacity-100 focus-within:opacity-100',
          message.role === 'user' ? 'justify-end' : 'justify-start'
        )}
      >
        <button
          type="button"
          onClick={() => onCopyMessage(message)}
          className="inline-flex h-7 items-center gap-1 rounded-md px-2 text-xs transition-colors hover:bg-muted hover:text-foreground"
          aria-label="Sao chép tin nhắn"
          title="Sao chép"
        >
          {copiedMessageId === message.id ? (
            <Check className="h-3.5 w-3.5 text-primary" />
          ) : (
            <Copy className="h-3.5 w-3.5" />
          )}
          <span>{copiedMessageId === message.id ? 'Đã copy' : 'Copy'}</span>
        </button>
        <button
          type="button"
          onClick={() => onEditMessage(message)}
          className="inline-flex h-7 items-center gap-1 rounded-md px-2 text-xs transition-colors hover:bg-muted hover:text-foreground"
          aria-label="Sửa tin nhắn"
          title="Sửa"
        >
          <Pencil className="h-3.5 w-3.5" />
          <span>Sửa</span>
        </button>
      </div>
    </div>
  </div>
))
MessageRow.displayName = 'MessageRow'

function collectConversationSources(messages: Message[]): SourceChunk[] {
  const seen = new Set<string>()
  const sources: SourceChunk[] = []

  messages.forEach((message) => {
    if (message.role !== 'assistant' || !message.sources?.length) return

    message.sources.forEach((rawSource, index) => {
      const source = rawSource as SourceChunk & CitationSource
      const sourceId =
        source.chunk_id ||
        source.id ||
        `${message.id}-source-${index}`
      const dedupeKey =
        sourceId ||
        `${source.document_id || source.title || source.source || 'source'}-${source.content || source.snippet || index}`

      if (seen.has(dedupeKey)) return
      seen.add(dedupeKey)

      sources.push({
        ...source,
        id: sourceId,
        chunk_id: source.chunk_id || sourceId,
        content: source.content || source.snippet || '',
        score: typeof source.score === 'number'
          ? source.score
          : typeof source.grounding_score === 'number'
            ? source.grounding_score
            : 0.9,
        document_id: source.document_id,
        chunk_index: source.chunk_index,
        title: source.title || source.source || 'Tài liệu',
        type: source.type,
      })
    })
  })

  return sources
}

// ==================== Main Component ====================

export function SimpleChat({
  messages,
  optimisticMessages,
  isLoading,
  onSendMessage,
  onStopGenerating,
  onClearChat,
  error,
  className,
  activeConversationId = null,
  isNewChat = true,
  isOptimistic = false,
  retryMessage,
  isRetryable = false,
  errorType
}: SimpleChatProps) {
  const sources = useSourcesStore((state) => state.sources)
  const isSourcesOpen = useSourcesStore((state) => state.isOpen)
  const activeSourceId = useSourcesStore((state) => state.activeSourceId)
  const setSources = useSourcesStore((state) => state.setSources)
  const setSourcesOpen = useSourcesStore((state) => state.setIsOpen)
  const setActiveSourceId = useSourcesStore((state) => state.setActiveSourceId)
  const replaceSourcesForConversation = useSourcesStore((state) => state.replaceForConversation)
  const resetSources = useSourcesStore((state) => state.reset)
  const [input, setInput] = useState('')
  const [sourcePanelOpen, setSourcePanelOpen] = useState(false)
  const [citationPanelOpen, setCitationPanelOpen] = useState(false)
  const [activeCitationChunkId, setActiveCitationChunkId] = useState<string | null>(null)
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null)
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


    return merged
  }, [messages, optimisticMessages])
  const conversationSources = useMemo(
    () => collectConversationSources(displayMessages),
    [displayMessages]
  )

  // Welcome screen state
  const [welcomeVisible, setWelcomeVisible] = useState(isNewChat)
  const [welcomeExiting, setWelcomeExiting] = useState(false)

  // Get latest assistant message with citations
  const latestAssistantMessage = messages.filter(m => m.role === 'assistant').pop()
  const hasNewCitationFormat = latestAssistantMessage?.use_new_citation_format
  const citationSources = hasNewCitationFormat ? (latestAssistantMessage?.sources as unknown as CitationSource[]) : undefined
  const verificationStats = latestAssistantMessage?.citation_verification
  const scrollAnchorSpacerHeight = (isLoading || isOptimistic) ? 'calc(100dvh - 220px)' : 0

  // ==================== Effects ====================

  useEffect(() => {
    if (isNewChat || !activeConversationId) {
      resetSources()
      return
    }

    replaceSourcesForConversation(activeConversationId, conversationSources)
  }, [
    activeConversationId,
    conversationSources,
    isNewChat,
    replaceSourcesForConversation,
    resetSources,
  ])

  /**
   * Auto-scroll to bottom on new messages
   * Scrolls smoothly when new messages arrive or content updates during streaming
   */
  const prevMessagesLengthRef = useRef<number>(0)
  const prevLatestUserMessageIdRef = useRef<string | null>(null)
  const didInitializeScrollTrackingRef = useRef<boolean>(false)
  const isUserScrolledRef = useRef<boolean>(false)
  const topAlignedUserMessageIdRef = useRef<string | null>(null)
  const pendingTopScrollMessageIdRef = useRef<string | null>(null)

  const scrollMessageToTop = useCallback((messageId: string, behavior: ScrollBehavior = 'smooth') => {
    const container = messagesContainerRef.current
    if (!container) {
      pendingTopScrollMessageIdRef.current = messageId
      return
    }

    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        const target = container.querySelector<HTMLElement>(
          `[data-message-id="${CSS.escape(messageId)}"]`
        )

        if (!target) {
          pendingTopScrollMessageIdRef.current = messageId
          return
        }

        const containerRect = container.getBoundingClientRect()
        const targetRect = target.getBoundingClientRect()
        const nextTop = container.scrollTop + targetRect.top - containerRect.top - 16

        container.scrollTo({
          top: Math.max(nextTop, 0),
          behavior,
        })
        pendingTopScrollMessageIdRef.current = null
        topAlignedUserMessageIdRef.current = messageId
        isUserScrolledRef.current = false
      })
    })
  }, [])

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

    const latestUserMessage = [...displayMessages].reverse().find((message) => message.role === 'user')
    const isNewMessage = displayMessages.length > prevMessagesLengthRef.current
    const isNewUserMessage =
      !!latestUserMessage &&
      latestUserMessage.id !== prevLatestUserMessageIdRef.current

    if (!didInitializeScrollTrackingRef.current) {
      didInitializeScrollTrackingRef.current = true
      prevMessagesLengthRef.current = displayMessages.length
      prevLatestUserMessageIdRef.current = latestUserMessage?.id ?? null
      return
    }

    if (isNewUserMessage && (isLoading || isOptimistic)) {
      pendingTopScrollMessageIdRef.current = latestUserMessage.id
      scrollMessageToTop(latestUserMessage.id)
      prevMessagesLengthRef.current = displayMessages.length
      prevLatestUserMessageIdRef.current = latestUserMessage.id
      return
    }

    const shouldKeepUserMessageAtTop =
      (isLoading || isOptimistic) &&
      (topAlignedUserMessageIdRef.current || pendingTopScrollMessageIdRef.current)
    const shouldAutoScroll =
      (isNewMessage && !shouldKeepUserMessageAtTop) ||
      (isLoading && !isUserScrolledRef.current && !shouldKeepUserMessageAtTop)

    if (shouldAutoScroll) {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: isNewMessage ? 'smooth' : 'auto'
      })
    }

    if (!isLoading) {
      topAlignedUserMessageIdRef.current = null
    }

    prevMessagesLengthRef.current = displayMessages.length
    prevLatestUserMessageIdRef.current = latestUserMessage?.id ?? null
  }, [displayMessages, isLoading, isOptimistic, scrollMessageToTop])

  useEffect(() => {
    if (welcomeVisible) return
    const pendingMessageId = pendingTopScrollMessageIdRef.current
    if (pendingMessageId) {
      scrollMessageToTop(pendingMessageId)
    }
  }, [welcomeVisible, displayMessages, scrollMessageToTop])

  /**
   * Sync welcomeVisible with isNewChat prop
   */
  useEffect(() => {
    setWelcomeVisible(isNewChat)
    setWelcomeExiting(false)
  }, [isNewChat])

  /**
   * Handle welcome screen fade-out
   */
  useEffect(() => {
    // Only fade out if we have messages AND (we are not in a new chat OR at least one message is optimistic/new)
    const hasNewChatMessages = displayMessages.length > 0 && (!isNewChat || displayMessages.some(msg => msg.isOptimistic))

    if (hasNewChatMessages && welcomeVisible) {
      setWelcomeExiting(true)
      const timer = setTimeout(() => {
        setWelcomeVisible(false)
        setWelcomeExiting(false)
      }, 300)
      return () => clearTimeout(timer)
    }
  }, [displayMessages, welcomeVisible, isNewChat])

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

  const handleStopGenerating = useCallback(() => {
    onStopGenerating?.()
  }, [onStopGenerating])

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

  const handleCopyMessage = useCallback(async (message: Message) => {
    try {
      await navigator.clipboard.writeText(message.content || '')
      setCopiedMessageId(message.id)
      window.setTimeout(() => {
        setCopiedMessageId((current) => current === message.id ? null : current)
      }, 1600)
    } catch (err) {
      console.error('Failed to copy message:', err)
    }
  }, [])

  const handleEditMessage = useCallback((message: Message) => {
    setInput(message.content || '')
    requestAnimationFrame(() => {
      textareaRef.current?.focus()
      const length = message.content.length
      textareaRef.current?.setSelectionRange(length, length)
    })
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
      const citation = (source || (allSources || message?.sources || [])[citationIndex]) as unknown as CitationSource
      setActiveCitationChunkId(citation?.chunk_id || (citation as any)?.id || null)
      setCitationPanelOpen(true)
    } else {
      // Use old SourcePanel
      const citationSources = allSources || messages.find(m => m.id === source.id)?.sources || []
      setSources(citationSources)
      setSourcesOpen(true)
      const targetId = source.chunk_id || source.id || `source-${citationIndex}`
      setActiveSourceId(targetId)
    }
  }, [messages, setActiveSourceId, setSources, setSourcesOpen])

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
                  copiedMessageId={copiedMessageId}
                  onCitationClick={(idx, src) => handleCitationClick(idx, src, message.sources)}
                  onCopyMessage={handleCopyMessage}
                  onEditMessage={handleEditMessage}
                />
              ))}

              <div ref={bottomRef} />
              <div
                aria-hidden="true"
                className="shrink-0 transition-[height] duration-200"
                style={{ height: scrollAnchorSpacerHeight }}
              />
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
                type={isLoading ? 'button' : 'submit'}
                onClick={isLoading ? handleStopGenerating : undefined}
                disabled={!isLoading && !input.trim()}
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
                title={isLoading ? 'Dừng sinh câu trả lời' : 'Gửi tin nhắn'}
                aria-label={isLoading ? 'Dừng sinh câu trả lời' : 'Gửi tin nhắn'}
              >
                {isLoading ? (
                  <Square className="w-4 h-4 fill-current" />
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
        sources={sources.map((s) => ({
          id: s.id,
          content: s.snippet,
          score: s.score,
          document_id: s.document_id || undefined,
          chunk_index: s.page !== undefined ? s.page - 1 : undefined,
        }))}
        isOpen={isSourcesOpen || sourcePanelOpen}
        onClose={() => {
          setSourcesOpen(false)
          setSourcePanelOpen(false)
        }}
        activeSourceId={activeSourceId}
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
