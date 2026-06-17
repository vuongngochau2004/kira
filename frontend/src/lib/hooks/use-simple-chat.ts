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
} from '@/lib/streaming'

// ==================== Types ====================

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sources?: SourceChunk[]
  attachments?: Attachment[]
  streamingState?: StreamingState
  isStreaming?: boolean
  isOptimistic?: boolean
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

// ==================== Custom Hook ====================

export function useSimpleChat() {
  // Store & Router
  const { activeConversationId, setActiveConversation, updateURL } = useConversationStore()
  const { isAuthenticated } = useAuthStore()
  const sourcesStore = useSourcesStore()

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
  const conversationError = useRef<any>(null)

  // Refs for streaming
  const abortControllerRef = useRef<AbortController | null>(null)
  const stateBuilderRef = useRef<ReturnType<typeof createStreamingStateBuilder> | null>(null)
  const assistantMsgIdRef = useRef<string | null>(null)

  // Effects
  useEffect(() => { setMounted(true) }, [])

  useEffect(() => { return () => { cleanup() } }, [])

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
    setMessages([])
    sourcesStore.replaceForConversation(activeConversationId, [])
    loadConversation(activeConversationId)
  }, [activeConversationId, mounted, isAuthenticated, isCreatingConversation])

  useEffect(() => {
    if (!activeConversationId && mounted && isAuthenticated && !isCreatingConversation) {
      cleanup()
      queueRef.current = new MessageQueue()
      failedMessageRef.current = null
      conversationError.current = null
      setError(null)
      setMessages([])
      // Reset sources panel when switching to new chat
      sourcesStore.reset()
    }
  }, [activeConversationId, mounted, isAuthenticated, isCreatingConversation])

  // ==================== Helpers ====================

  function cleanup() {
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
  }

  /**
   * Update assistant message with current streaming state
   * Simple mapping: state → hierarchy → message
   */
  function updateAssistantMessage(msgId: string | null, stateBuilder: ReturnType<typeof createStreamingStateBuilder>) {
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
              streamingState: state.status,
              isStreaming: state.status !== 'complete',
            }
          : msg
      )
    )
  }

  function finishCurrentAssistantMessage() {
    const assistantMsgId = assistantMsgIdRef.current
    if (!assistantMsgId) return

    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === assistantMsgId
          ? {
              ...msg,
              streamingState: 'complete' as const,
              isStreaming: false,
            }
          : msg
      )
    )
  }

  async function loadConversation(id: string) {
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
                (msg.sources as SourceChunk[]) || (metadata?.sources as SourceChunk[]) || undefined
              ) as SourceChunk[] | undefined,
              attachments: (metadata?.attachments as Attachment[]) || undefined,
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
    } catch (err) {
      // Silent fail
    }
  }

  async function flushQueuedMessages(conversationId: string) {
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

        try {
          const abortController = new AbortController()
          abortControllerRef.current = abortController
          const stream = chatAPI.streamMessage(queuedMsg.content, conversationId, abortController.signal)
          let contentChunkCount = 0

          for await (const chunk of stream) {
            const { type, data: eventData } = chunk

            if (type === 'error') {
              const errorMsg = eventData?.error || eventData?.message || 'Server error occurred'
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
            if (type === 'content') {
              contentChunkCount += 1
              if (contentChunkCount % STREAM_PAINT_INTERVAL_CHUNKS === 0) {
                await waitForNextPaint()
              }
            }
          }
          abortControllerRef.current = null

          // Mark optimistic messages as real
          setMessages((prev) =>
            prev.map(msg => msg.id.startsWith('temp-')
              ? { ...msg, isOptimistic: false }
              : msg
            )
          )
        } catch (streamErr: any) {
          if (streamErr?.name === 'AbortError') {
            finishCurrentAssistantMessage()
            return
          }

          const errorMsg = streamErr?.message || 'Failed to stream response'
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
      })
    } catch (err: any) {
      setError(err?.message || 'Failed to send queued messages')
    }
  }

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

      try {
        const stateBuilder = createStreamingStateBuilder()
        stateBuilderRef.current = stateBuilder

        const abortController = new AbortController()
        abortControllerRef.current = abortController
        const stream = chatAPI.streamMessage(content.trim(), activeConversationId, abortController.signal)
        let contentChunkCount = 0

        for await (const chunk of stream) {
          const { type, data: eventData } = chunk

          if (type === 'error') {
            const errorMsg = eventData?.error || eventData?.message || 'Server error occurred'
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
          if (type === 'content') {
            contentChunkCount += 1
            if (contentChunkCount % STREAM_PAINT_INTERVAL_CHUNKS === 0) {
              await waitForNextPaint()
            }
          }
        }
      } catch (err: any) {
        if (err.name === 'AbortError') {
          finishCurrentAssistantMessage()
        } else {
          const errorMsg = err?.message || 'Failed to send message. Please check your connection.'
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
        setIsLoading(false)
        abortControllerRef.current = null
      }
      return
    }

    // FIRST MESSAGE PATH - Optimistic conversation creation
    const tempUserMsgId = `temp-user-${Date.now()}`
    const tempAssistantMsgId = `temp-assistant-${Date.now()}`

    const tempUserMessage: Message = {
      id: tempUserMsgId,
      role: 'user',
      content: content.trim(),
      timestamp: new Date(),
      isOptimistic: true,
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

        setActiveConversation(newConversationId)
        await flushQueuedMessages(newConversationId)

        setMessages((prev) =>
          prev.map(msg => msg.id.startsWith('temp-')
            ? { ...msg, isOptimistic: false }
            : msg
          )
        )
        setIsCreatingConversation(false)
      } catch (err: any) {
        setError(err?.message || 'Failed to create conversation. Please try again.')
        failedMessageRef.current = content
        queueRef.current = new MessageQueue()
        setIsCreatingConversation(false)
        setMessages((prev) => prev.filter(msg => !msg.id.startsWith('temp-')))
      }
    }
  }, [
    activeConversationId,
    setActiveConversation,
    cleanup,
    isCreatingConversation,
    addOptimistic,
    isAuthenticated,
    mounted,
  ])

  const clearMessages = useCallback(() => {
    cleanup()
    setMessages([])
    setActiveConversation(null)
    setError(null)
    // Reset sources panel
    sourcesStore.reset()
  }, [setActiveConversation, cleanup])

  const retryMessage = useCallback(() => {
    if (failedMessageRef.current) {
      setError(null)
      sendMessage(failedMessageRef.current)
      failedMessageRef.current = null
    }
  }, [sendMessage])

  const stopGenerating = useCallback(() => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    finishCurrentAssistantMessage()
    setIsLoading(false)
  }, [])

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
