/**
 * useSimpleChat - Simple, clean chat hook with streaming support
 *
 * Architecture: Send Message → Stream → Update State → Render
 * No complex parsing, just accumulate and display
 */

'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { conversationsAPI, chatAPI } from '@/lib/api/simple-client'
import { useConversationStore } from '@/lib/stores/conversation-store'
import { useAuthStore } from '@/lib/stores/auth-store'
import { useSourcesStore } from '@/lib/stores/sources-store'
import { useOptimistic, useTransition } from 'react'
import { MessageQueue, type QueuedMessage } from '@/lib/utils/message-queue'
import {
  createStreamingStateBuilder,
  ensureFlatSources,
  type StreamingState,
  type SourceChunk,
  type Attachment,
  type RawCitationItem,
  type PipelineStep,
  toPipelineSteps,
} from '@/lib/streaming'
import { toLegalAnswerInfo } from '@/lib/legal/format'
import type { LegalAnswerInfo } from '@/lib/legal/types'

function getStreamErrorMessage(data: unknown): string {
  if (typeof data !== 'object' || data === null) return 'Server error occurred'
  const payload = data as Record<string, unknown>
  if (typeof payload.error === 'string') return payload.error
  if (typeof payload.message === 'string') return payload.message
  if (typeof payload.error === 'object' && payload.error !== null) {
    const nested = payload.error as Record<string, unknown>
    if (typeof nested.message === 'string') return nested.message
  }
  return 'Server error occurred'
}

// ==================== Types ====================

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sources?: SourceChunk[]
  attachments?: Attachment[]
  streamingState?: StreamingState
  provisional?: boolean
  isStreaming?: boolean
  isOptimistic?: boolean
  unsaved?: boolean
  legal?: LegalAnswerInfo
  pipeline?: PipelineStep[]
}

// ==================== Constants ====================

const STREAM_PAINT_INTERVAL_CHUNKS = 3

// ==================== Helpers ====================

function waitForNextPaint(): Promise<void> {
  if (typeof window === 'undefined') {
    return Promise.resolve()
  }

  return new Promise((resolve) => {
    window.requestAnimationFrame(() => resolve())
  })
}

function getErrorMessage(err: unknown, defaultMsg: string): string {
  if (err instanceof Error) return err.message
  if (typeof err === 'object' && err !== null && 'message' in err) {
    return String((err as { message: unknown }).message)
  }
  return defaultMsg
}

function isAbortError(err: unknown): boolean {
  if (err instanceof Error && err.name === 'AbortError') return true
  if (typeof err === 'object' && err !== null && 'name' in err) {
    return (err as { name: unknown }).name === 'AbortError'
  }
  return false
}

// ==================== Custom Hook ====================

export function useSimpleChat() {
  // Store & Router
  const { activeConversationId, setActiveConversation } = useConversationStore()
  const { isAuthenticated } = useAuthStore()
  // Select stable actions only: subscribing to the whole store would give effects a new
  // dependency on every store update and loop with SimpleChat's own source sync.
  const replaceSourcesForConversation = useSourcesStore((state) => state.replaceForConversation)
  const resetSources = useSourcesStore((state) => state.reset)

  // State
  const [mounted, setMounted] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Optimistic
  const [isPending, startTransition] = useTransition()
  const [optimisticMessages, addOptimistic] = useOptimistic(
    messages,
    (state, newMessage: Message) => {
      const existingIndex = state.findIndex(m => m.id === newMessage.id)
      if (existingIndex !== -1) {
        const updated = [...state]
        updated[existingIndex] = { ...newMessage, isOptimistic: false }
        return updated
      }
      return [...state, { ...newMessage, isOptimistic: true }]
    }
  )

  const [isCreatingConversation, setIsCreatingConversation] = useState(false)
  const queueRef = useRef(new MessageQueue())
  const failedMessageRef = useRef<string | null>(null)
  const conversationError = useRef<{ type?: string; retryable?: boolean } | null>(null)

  // Refs for streaming
  const abortControllerRef = useRef<AbortController | null>(null)
  const stateBuilderRef = useRef<ReturnType<typeof createStreamingStateBuilder> | null>(null)
  const assistantMsgIdRef = useRef<string | null>(null)
  const skipConversationLoadForRef = useRef<string | null>(null)


  // ==================== Helpers ====================

  const cleanup = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    if (stateBuilderRef.current) {
      stateBuilderRef.current.reset()
      stateBuilderRef.current = null
    }
    assistantMsgIdRef.current = null
    setIsLoading(false)
  }, [])

  /**
   * Update assistant message with current streaming state
   * Simple mapping: state → hierarchy → message
   */
  const updateAssistantMessage = useCallback(
    (msgId: string | null, stateBuilder: ReturnType<typeof createStreamingStateBuilder>) => {
      if (!msgId) return

      const state = stateBuilder.getState()

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === msgId
            ? {
                ...msg,
                content: state.content,
                sources: state.sources.length > 0 ? [...state.sources] : undefined,
                attachments: state.attachments.length > 0 ? [...state.attachments] : undefined,
                legal: state.legal ?? undefined,
                pipeline: state.pipeline.length > 0 ? state.pipeline : undefined,
                streamingState: state.status,
                provisional: state.provisional,
                isStreaming: !['complete', 'stopped', 'error'].includes(state.status),
              }
            : msg
        )
      )
    },
    []
  )

  const finishCurrentAssistantMessage = useCallback(() => {
    const assistantMsgId = assistantMsgIdRef.current
    if (!assistantMsgId) return

    const builder = stateBuilderRef.current
    const persisted = builder?.getState().finalized === true
    if (!persisted) builder?.stop()

    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === assistantMsgId
          ? {
              ...msg,
              streamingState: persisted ? 'complete' as const : 'stopped' as const,
              isStreaming: false,
              provisional: !persisted,
              sources: persisted ? msg.sources : undefined,
            }
          : msg
      )
    )
  }, [])

  const markUserMessageSaved = useCallback((messageId: string): void => {
    setMessages((prev) => prev.map((message) => message.id === messageId
      ? { ...message, unsaved: false }
      : message
    ))
  }, [])

  const loadConversation = useCallback(async (id: string) => {
    try {
      const conversation = await conversationsAPI.get(id)

      setMessages(
        conversation.messages.map((msg) => {
          if (msg.role === 'assistant') {
            const msgObj = msg as unknown as Record<string, unknown>
            const metadata = msgObj.metadata as Record<string, unknown> | null

            return {
              id: msg.id,
              role: 'assistant' as const,
              content: msg.content || '',
              timestamp: new Date(msg.created_at),
              sources: ensureFlatSources(
                (msg.sources as RawCitationItem[] | undefined) ||
                (metadata?.sources as RawCitationItem[] | undefined)
              ),
              attachments: (metadata?.attachments as Attachment[]) || undefined,
              legal: toLegalAnswerInfo(metadata?.legal),
              pipeline: toPipelineSteps(metadata?.pipeline),
              streamingState: 'complete' as const,
              isStreaming: false,
            }
          }

          return {
            id: msg.id,
            role: 'user' as const,
            content: msg.content,
            timestamp: new Date(msg.created_at),
            isStreaming: false,
          }
        })
      )
    } catch {
      // Silent fail
    }
  }, [])

  const flushQueuedMessages = useCallback(
    async (conversationId: string) => {
      const queue = queueRef.current

      if (queue.isEmpty()) {
        return
      }

      try {
        await queue.flush(async (queuedMsg: QueuedMessage) => {
          const assistantMsgId = queuedMsg.assistantId || (Date.now() + Math.random()).toString()
          assistantMsgIdRef.current = assistantMsgId

          const stateBuilder = createStreamingStateBuilder()
          stateBuilderRef.current = stateBuilder

          // Set initial assistant message
          setMessages((prev) => {
            const existingMsg = prev.find(m => m.id === assistantMsgId)
            return [
              ...prev.filter(m => m.id !== assistantMsgId),
              {
                id: assistantMsgId,
                role: 'assistant' as const,
                content: '',
                timestamp: new Date(),
                sources: existingMsg?.sources || [],
                streamingState: 'connecting',
                isStreaming: true,
                isOptimistic: false,
              }
            ]
          })

          const abortController = new AbortController()
          abortControllerRef.current = abortController
          setIsLoading(true)
          try {
            const stream = chatAPI.streamMessage(queuedMsg.content, conversationId, abortController.signal)
            let contentChunkCount = 0
            let streamFailed = false

            for await (const chunk of stream) {
              if (abortController.signal.aborted || abortControllerRef.current !== abortController) break
              const { type, data: eventData } = chunk

              if (type === 'error') {
                streamFailed = true
                const errorMsg = getStreamErrorMessage(eventData)
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMsgId
                      ? {
                          ...msg,
                          streamingState: 'error' as const,
                          isStreaming: false,
                          content: `❌ Error: ${errorMsg}`,
                        }
                      : msg
                  )
                )
                break
              }

              stateBuilder.processChunk(type, eventData)
              updateAssistantMessage(assistantMsgId, stateBuilder)
              if (type === 'metadata') markUserMessageSaved(queuedMsg.id)
              if (type === 'content') {
                contentChunkCount += 1
                if (contentChunkCount % STREAM_PAINT_INTERVAL_CHUNKS === 0) {
                  await waitForNextPaint()
                }
              }
            }
            if (!abortController.signal.aborted && !streamFailed && !stateBuilder.getState().finalized) {
              setMessages((prev) => prev.map((msg) => msg.id === assistantMsgId
                ? { ...msg, content: '❌ Kết nối bị ngắt trước khi câu trả lời hoàn tất.', streamingState: 'error', isStreaming: false, provisional: false }
                : msg
              ))
            }
            // Mark optimistic messages as real
            setMessages((prev) =>
              prev.map(msg => msg.id.startsWith('temp-')
                ? { ...msg, isOptimistic: false }
                : msg
              )
            )
          } catch (streamErr: unknown) {
            if (isAbortError(streamErr) || abortController.signal.aborted) {
              if (assistantMsgIdRef.current !== assistantMsgId) return
              finishCurrentAssistantMessage()
              return
            }

            const errorMsg = getErrorMessage(streamErr, 'Failed to stream response')
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMsgId
                  ? {
                      ...msg,
                      streamingState: 'error' as const,
                      isStreaming: false,
                      content: `❌ ${errorMsg}`,
                    }
                  : msg
              )
            )
          } finally {
            if (abortControllerRef.current === abortController) {
              abortControllerRef.current = null
              setIsLoading(false)
            }
          }
        })
      } catch (err: unknown) {
        setError(getErrorMessage(err, 'Failed to send queued messages'))
      }
    },
    [updateAssistantMessage, finishCurrentAssistantMessage, markUserMessageSaved]
  )

  // ==================== Effects ====================

  useEffect(() => { setMounted(true) }, [])

  useEffect(() => { return () => { cleanup() } }, [cleanup])

  useEffect(() => {
    return () => {
      if (isCreatingConversation) {
        queueRef.current = new MessageQueue()
        setIsCreatingConversation(false)
      }
    }
  }, [isCreatingConversation])

  useEffect(() => {
    if (!activeConversationId || !mounted || !isAuthenticated || isCreatingConversation) {
      return
    }
    if (skipConversationLoadForRef.current === activeConversationId) {
      skipConversationLoadForRef.current = null
      return
    }
    skipConversationLoadForRef.current = null
    setMessages([])
    replaceSourcesForConversation(activeConversationId, [])
    loadConversation(activeConversationId)
  }, [activeConversationId, mounted, isAuthenticated, isCreatingConversation, loadConversation, replaceSourcesForConversation])

  useEffect(() => {
    if (!activeConversationId && mounted && isAuthenticated && !isCreatingConversation) {
      cleanup()
      queueRef.current = new MessageQueue()
      failedMessageRef.current = null
      conversationError.current = null
      setError(null)
      setMessages([])
      // Reset sources panel when switching to new chat
      resetSources()
    }
  }, [activeConversationId, mounted, isAuthenticated, isCreatingConversation, cleanup, resetSources])

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return

    if (isLoading || isCreatingConversation) {
      console.warn('[useSimpleChat] Message send blocked: already processing')
      return
    }

    setError(null)
    failedMessageRef.current = null

    if (activeConversationId) {
      cleanup()
      setIsLoading(true)

      const userMsgId = Date.now().toString()
      const assistantMsgId = (Date.now() + 1).toString()
      assistantMsgIdRef.current = assistantMsgId

      const userMessage: Message = {
        id: userMsgId,
        role: 'user',
        content: content.trim(),
        timestamp: new Date(),
        isStreaming: false,
        unsaved: true,
      }

      const assistantMessage: Message = {
        id: assistantMsgId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        streamingState: 'connecting',
        isStreaming: true,
      }

      setMessages((prev) => [...prev, userMessage, assistantMessage])

      const abortController = new AbortController()
      abortControllerRef.current = abortController
      try {
        const stateBuilder = createStreamingStateBuilder()
        stateBuilderRef.current = stateBuilder

        const stream = chatAPI.streamMessage(content.trim(), activeConversationId, abortController.signal)
        let contentChunkCount = 0
        let streamFailed = false

        for await (const chunk of stream) {
          if (abortController.signal.aborted || abortControllerRef.current !== abortController) break
          const { type, data: eventData } = chunk

          if (type === 'error') {
            streamFailed = true
            const errorMsg = getStreamErrorMessage(eventData)
            setError(errorMsg)
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMsgId
                  ? {
                      ...msg,
                      streamingState: 'error' as const,
                      isStreaming: false,
                      content: `❌ Error: ${errorMsg}`,
                    }
                  : msg
              )
            )
            break
          }

          stateBuilder.processChunk(type, eventData)
          updateAssistantMessage(assistantMsgId, stateBuilder)
          if (type === 'metadata') markUserMessageSaved(userMsgId)
          if (type === 'content') {
            contentChunkCount += 1
            if (contentChunkCount % STREAM_PAINT_INTERVAL_CHUNKS === 0) {
              await waitForNextPaint()
            }
          }
        }
        if (!abortController.signal.aborted && !streamFailed && !stateBuilder.getState().finalized) {
          setMessages((prev) => prev.map((msg) => msg.id === assistantMsgId
            ? { ...msg, content: '❌ Kết nối bị ngắt trước khi câu trả lời hoàn tất.', streamingState: 'error', isStreaming: false, provisional: false }
            : msg
          ))
        }
      } catch (err: unknown) {
        if (isAbortError(err) || abortController.signal.aborted) {
          if (assistantMsgIdRef.current !== assistantMsgId) return
          finishCurrentAssistantMessage()
        } else {
          const errorMsg = getErrorMessage(err, 'Failed to send message. Please check your connection.')
          setError(errorMsg)
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsgId
                ? {
                    ...msg,
                    streamingState: 'error' as const,
                    isStreaming: false,
                    content: `❌ ${errorMsg}`,
                  }
                : msg
            )
          )
        }
      } finally {
        if (abortControllerRef.current === abortController) {
          setIsLoading(false)
          abortControllerRef.current = null
        }
      }
      return
    }

    // FIRST MESSAGE PATH - Optimistic conversation creation
    const tempUserMsgId = `temp-user-${Date.now()}`
    const tempAssistantMsgId = `temp-assistant-${Date.now()}`
    assistantMsgIdRef.current = tempAssistantMsgId
    setIsLoading(true)

    const tempUserMessage: Message = {
      id: tempUserMsgId,
      role: 'user',
      content: content.trim(),
      timestamp: new Date(),
      isOptimistic: true,
      unsaved: true,
    }

    const tempAssistantMessage: Message = {
      id: tempAssistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isOptimistic: true,
      isStreaming: true,
      streamingState: 'connecting',
    }

    setMessages((prev) => [...prev, tempUserMessage, tempAssistantMessage])

    startTransition(() => {
      addOptimistic(tempUserMessage)
      addOptimistic(tempAssistantMessage)
    })

    queueRef.current.enqueue({
      id: tempUserMsgId,
      content: content.trim(),
      timestamp: new Date(),
      assistantId: tempAssistantMsgId,
    })

    if (!isCreatingConversation) {
      setIsCreatingConversation(true)

      try {
        const { id: newConversationId } = await conversationsAPI.create('web')

        const currentUrl = new URL(window.location.href)
        currentUrl.searchParams.set('id', newConversationId)
        window.history.replaceState({}, '', currentUrl.toString())

        skipConversationLoadForRef.current = newConversationId
        setActiveConversation(newConversationId)
        if (!queueRef.current.isEmpty()) {
          await flushQueuedMessages(newConversationId)
        }

        setMessages((prev) =>
          prev.map(msg => msg.id.startsWith('temp-')
            ? { ...msg, isOptimistic: false }
            : msg
          )
        )
        setIsCreatingConversation(false)
      } catch (err: unknown) {
        setError(getErrorMessage(err, 'Failed to create conversation. Please try again.'))
        failedMessageRef.current = content
        queueRef.current = new MessageQueue()
        setIsCreatingConversation(false)
        setMessages((prev) => prev.filter(msg => !msg.id.startsWith('temp-')))
        setIsLoading(false)
      }
    }
  }, [
    activeConversationId,
    setActiveConversation,
    cleanup,
    isCreatingConversation,
    addOptimistic,
    isLoading,
    flushQueuedMessages,
    updateAssistantMessage,
    finishCurrentAssistantMessage,
    markUserMessageSaved,
  ])

  const clearMessages = useCallback(() => {
    cleanup()
    setMessages([])
    setActiveConversation(null)
    setError(null)
    // Reset sources panel
    resetSources()
  }, [setActiveConversation, cleanup, resetSources])

  const retryMessage = useCallback(() => {
    if (failedMessageRef.current) {
      setError(null)
      sendMessage(failedMessageRef.current)
      failedMessageRef.current = null
    }
  }, [sendMessage])

  const stopGenerating = useCallback(() => {
    if (isCreatingConversation && !abortControllerRef.current) {
      queueRef.current = new MessageQueue()
    }
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    finishCurrentAssistantMessage()
    setIsLoading(false)
  }, [finishCurrentAssistantMessage, isCreatingConversation])

  return {
    messages,
    optimisticMessages,
    isLoading,
    error,
    isOptimistic: isPending || isCreatingConversation,
    sendMessage,
    stopGenerating,
    clearMessages,
    retryMessage,
    activeConversationId,
    errorType: conversationError.current?.type,
    isRetryable: conversationError.current?.retryable ?? false,
  }
}
