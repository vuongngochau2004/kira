/**
 * useSimpleChat - React hook for chat functionality with streaming support
 *
 * Architecture:
 * - SSE Client → StreamingStateBuilder → MessageState → UI Components
 * - Clean separation: parse → build → render
 * - Type-safe throughout
 */

'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { conversationsAPI, chatAPI } from '@/lib/api/simple-client'
import { useConversationStore } from '@/lib/stores/conversation-store'
import { useAuthStore } from '@/lib/stores/auth-store'
import { useOptimistic, useTransition } from 'react'
import { MessageQueue, type QueuedMessage } from '@/lib/utils/message-queue'
import { ConversationError, ConversationErrorType, getErrorUserMessage } from '@/lib/types/errors'
import {
  createStreamingStateBuilder,
  type MessageState as StreamingMessageState,
  type StreamingState,
  type SourceChunk,
} from '@/lib/streaming'
import type { ThinkingHierarchy, ThinkingHierarchy as ThinkingHierarchyType } from '@/types/thinking'

// ==================== Types ====================

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sources?: SourceChunk[]
  thinkingHierarchy?: ThinkingHierarchyType
  streamingState?: StreamingState
  isStreaming?: boolean
  isOptimistic?: boolean
}

// ==================== Constants ====================

const STREAM_TIMEOUT_MS = 30000 // 30s timeout

// ==================== Helpers ====================

/**
 * Convert StreamingMessageState to ThinkingHierarchy for UI rendering
 */
function messageStateToThinkingHierarchy(state: StreamingMessageState): ThinkingHierarchy | undefined {
  // DEBUG: Log what we're converting
  console.log('[messageStateToThinkingHierarchy] Converting state:', {
    hasRouting: !!state.routing,
    routing: state.routing,
    retrievalCount: state.retrieval.length,
    retrieval: state.retrieval,
    reasoningLength: state.reasoning?.length || 0,
    reasoningPreview: state.reasoning ? state.reasoning.substring(0, 100) + '...' : 'N/A',
    status: state.status
  })

  const hierarchy: ThinkingHierarchy = {
    execution: [],
    status: state.status === 'complete' ? 'complete' : 'running',
  }

  // Add routing if present
  if (state.routing) {
    const routerMatch = state.routing.router.match(/^(\w+)(?:\s+\((\w+)\))?/)
    if (routerMatch) {
      hierarchy.routing = {
        router: routerMatch[1],
        intent: routerMatch[2] || state.routing.intent,
        timestamp: state.timestamp,
      }
    }
  }

  // Add retrieval stages
  if (state.retrieval.length > 0) {
    hierarchy.execution = state.retrieval.map(stage => ({
      stage: 'retrieval' as const,
      iteration: stage.iteration,
      strategy: stage.strategy,
      docsRetrieved: stage.docsRetrieved,
      timestamp: state.timestamp,
    }))
  }

  // Add reasoning if present
  if (state.reasoning) {
    hierarchy.reasoning = {
      content: state.reasoning,
      isStreaming: state.status !== 'complete',
      timestamp: state.timestamp,
    }
  }

  // Only return if we have meaningful data
  if (hierarchy.routing || hierarchy.execution.length > 0 || hierarchy.reasoning) {
    console.log('[messageStateToThinkingHierarchy] Returning hierarchy:', {
      hasRouting: !!hierarchy.routing,
      hasExecution: hierarchy.execution.length > 0,
      hasReasoning: !!hierarchy.reasoning,
      reasoningLength: hierarchy.reasoning?.content?.length || 0
    })
    return hierarchy
  }

  console.log('[messageStateToThinkingHierarchy] Returning undefined - no data')
  return undefined
}

// ==================== Custom Hook ====================

export function useSimpleChat() {
  // ==================== Store & Router ====================
  const { activeConversationId, setActiveConversation, updateURL } = useConversationStore()
  const { isAuthenticated } = useAuthStore()

  // ==================== State ====================
  const [mounted, setMounted] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Optimistic state
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

  // Conversation creation state
  const [isCreatingConversation, setIsCreatingConversation] = useState(false)

  // Message queue for pending conversation
  const queueRef = useRef(new MessageQueue())
  const failedMessageRef = useRef<string | null>(null)

  // Typed error state
  const [conversationError, setConversationError] = useState<ConversationError | null>(null)

  // Refs for streaming
  const abortControllerRef = useRef<AbortController | null>(null)
  const stateBuilderRef = useRef<ReturnType<typeof createStreamingStateBuilder> | null>(null)
  const assistantMsgIdRef = useRef<string | null>(null)

  // ==================== Effects ====================

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    return () => {
      cleanup()
    }
  }, [])

  useEffect(() => {
    return () => {
      if (isCreatingConversation) {
        queueRef.current.clear()
        setIsCreatingConversation(false)
      }
    }
  }, [isCreatingConversation])

  // Load conversation when activeConversationId changes
  useEffect(() => {
    if (!activeConversationId || !mounted || !isAuthenticated || isCreatingConversation) {
      return
    }
    loadConversation(activeConversationId)
  }, [activeConversationId, mounted, isAuthenticated, isCreatingConversation])

  // Clear messages when no active conversation
  useEffect(() => {
    if (!activeConversationId && mounted && isAuthenticated && !isCreatingConversation) {
      setMessages([])
    }
  }, [activeConversationId, mounted, isAuthenticated, isCreatingConversation])

  // ==================== Helpers ====================

  /**
   * Cleanup stream and reset state
   */
  const cleanup = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    // CRITICAL: Reset state builder to prevent unbounded buffer growth
    if (stateBuilderRef.current) {
      stateBuilderRef.current.reset()
      stateBuilderRef.current = null
    }
    assistantMsgIdRef.current = null
    setIsLoading(false)
  }, [])

  /**
   * Update assistant message with current streaming state
   */
  const updateAssistantMessage = useCallback((
    msgId: string | null,
    stateBuilder: ReturnType<typeof createStreamingStateBuilder>
  ) => {
    if (!msgId) return

    const messageState = stateBuilder.getState()
    const thinkingHierarchy = messageStateToThinkingHierarchy(messageState)

    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === msgId
          ? {
              ...msg,
              content: messageState.content,
              thinkingHierarchy,
              sources: messageState.sources.length > 0 ? [...messageState.sources] : undefined,
              streamingState: messageState.status,
              isStreaming: messageState.status !== 'complete',
            }
          : msg
      )
    )
  }, [])

  /**
   * Load conversation from API
   */
  const loadConversation = async (id: string) => {
    try {
      const conversation = await conversationsAPI.get(id)

      setMessages(
        conversation.messages.map((msg) => {
          if (msg.role === 'assistant') {
            let content = msg.content || ''
            let extractedReasoning = ''

            // Parse thinking tags from content
            const thinkingMatch = content.match(/<thinking>([\s\S]*?)<\/thinking>/gi)
            if (thinkingMatch) {
              extractedReasoning = thinkingMatch
                .map(match => match.replace(/<\/?thinking[^>]*>/gi, '').trim())
                .join('\n\n')
              content = content.replace(/<thinking>[\s\S]*?<\/thinking>/gi, '').trim()
            }

            const thinkingData = (msg as any).thinking_data || null
            const isEmptyObject = thinkingData && typeof thinkingData === 'object' && Object.keys(thinkingData).length === 0
            const thinkingMetadata = (isEmptyObject || !thinkingData) ? null : (thinkingData?.thinking || thinkingData)

            let thinkingHierarchy: ThinkingHierarchy | undefined = undefined

            if (thinkingMetadata && typeof thinkingMetadata === 'object') {
              const routerName = thinkingMetadata.router || null
              const retrievalStages = thinkingMetadata.retrieval || []
              let reasoning = thinkingMetadata.reasoning || extractedReasoning || ''
              reasoning = reasoning.replace(/<\/?thinking[^>]*>/gi, '').trim()

              const hasThinkingData = routerName || retrievalStages.length > 0 || reasoning

              if (hasThinkingData) {
                const hierarchy: ThinkingHierarchy = {
                  execution: [],
                  status: 'complete',
                }

                if (routerName) {
                  const routerMatch = routerName.match(/^(\w+)(?:\s+\((\w+)\))?/)
                  if (routerMatch) {
                    hierarchy.routing = {
                      router: routerMatch[1],
                      intent: routerMatch[2],
                      timestamp: new Date(msg.created_at).getTime(),
                    }
                  }
                }

                if (retrievalStages.length > 0) {
                  hierarchy.execution = retrievalStages.map((stage: any) => ({
                    stage: 'retrieval' as const,
                    iteration: stage.iteration || 1,
                    strategy: (stage.strategy?.toLowerCase() === 'hybrid' ? 'hybrid' : 'dense') as 'dense' | 'hybrid',
                    docsRetrieved: stage.docs_retrieved || 0,
                    timestamp: new Date(msg.created_at).getTime(),
                  }))
                }

                if (reasoning) {
                  hierarchy.reasoning = {
                    content: reasoning,
                    isStreaming: false,
                    timestamp: new Date(msg.created_at).getTime(),
                  }
                }

                thinkingHierarchy = hierarchy
              }
            }

            if (!thinkingHierarchy && extractedReasoning) {
              thinkingHierarchy = {
                execution: [],
                status: 'complete',
                reasoning: {
                  content: extractedReasoning.replace(/<\/?thinking[^>]*>/gi, '').trim(),
                  isStreaming: false,
                  timestamp: new Date(msg.created_at).getTime(),
                },
              }
            }

            return {
              id: msg.id,
              role: 'assistant' as const,
              content: content,
              timestamp: new Date(msg.created_at),
              thinkingHierarchy,
              sources: msg.sources || (msg.metadata as any)?.sources || undefined,
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
      // Silent fail on conversation load error
    }
  }

  /**
   * Flush queued messages after conversation is created
   */
  const flushQueuedMessages = useCallback(async (conversationId: string) => {
    const queue = queueRef.current

    if (queue.isEmpty()) {
      return
    }

    try {
      await queue.flush(async (queuedMsg: QueuedMessage) => {
        const assistantMsgId = queuedMsg.assistantId || (Date.now() + Math.random()).toString()
        assistantMsgIdRef.current = assistantMsgId

        // Create new state builder for this message
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
              thinkingHierarchy: existingMsg?.thinkingHierarchy || {
                status: 'running',
                execution: [],
              },
              sources: existingMsg?.sources || [],
              streamingState: 'connecting',
              isStreaming: true,
            }
          ]
        })

        try {
          // Stream response
          const stream = chatAPI.streamMessage(queuedMsg.content, conversationId)

          for await (const chunk of stream) {
            const { type, data: eventData } = chunk

            // Check for error chunks from server
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
          }

          // Clean up optimistic messages
          setMessages((prev) => prev.filter(msg => !msg.id.startsWith('temp-user-')))
        } catch (streamErr: any) {
          // IMPROVED: Better error handling for individual message streaming
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
      queue.clear()
    }
  }, [updateAssistantMessage])

  /**
   * Send message and handle streaming response
   */
  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return

    // CRITICAL: Prevent race condition - check if already processing
    if (isLoading || isCreatingConversation) {
      console.warn('[useSimpleChat] Message send blocked: already processing')
      return
    }

    // Clear previous errors
    setError(null)
    failedMessageRef.current = null

    // If we have an active conversation, send normally
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
        // Create state builder for streaming
        const stateBuilder = createStreamingStateBuilder()
        stateBuilderRef.current = stateBuilder

        const stream = chatAPI.streamMessage(content.trim(), activeConversationId)

        let timeoutId: NodeJS.Timeout | null = null

        // IMPROVED: Better timeout handling with cleanup
        timeoutId = setTimeout(() => {
          if (abortControllerRef.current) {
            abortControllerRef.current.abort()
            setError('Streaming timeout - please try again')
            // Update assistant message to show error
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMsgId
                  ? {
                      ...msg,
                      streamingState: 'error' as const,
                      isStreaming: false,
                      content: '⏱️ Request timeout. Please try again.',
                    }
                  : msg
              )
            )
          }
        }, STREAM_TIMEOUT_MS)

        for await (const chunk of stream) {
          const { type, data: eventData } = chunk

          // Check for error chunks from server
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
        }

        // Clear timeout if stream completed successfully
        if (timeoutId) {
          clearTimeout(timeoutId)
        }
      } catch (err: any) {
        // IMPROVED: Better error handling with user-visible feedback
        if (err.name === 'AbortError') {
          // User cancelled or timeout - show cancellation message
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsgId
                ? {
                    ...msg,
                    streamingState: 'error' as const,
                    isStreaming: false,
                    content: '⚠️ Request cancelled or timed out.',
                  }
                : msg
            )
          )
        } else {
          // Network or other errors - show error to user
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
      thinkingHierarchy: {
        status: 'running',
        execution: [],
      },
    }

    // Show optimistic messages immediately
    startTransition(() => {
      addOptimistic(tempUserMessage)
      addOptimistic(tempAssistantMessage)
    })

    setMessages((prev) => [...prev, tempAssistantMessage])

    // Queue the message
    queueRef.current.enqueue({
      id: tempUserMsgId,
      content: content.trim(),
      timestamp: new Date(),
      assistantId: tempAssistantMsgId,
    })

    // Start conversation creation
    if (!isCreatingConversation) {
      setIsCreatingConversation(true)

      try {
        const { id: newConversationId } = await conversationsAPI.create('web')

        // Update URL
        const currentUrl = new URL(window.location.href)
        currentUrl.searchParams.set('id', newConversationId)
        window.history.replaceState({}, '', currentUrl.toString())

        setActiveConversation(newConversationId)
        await flushQueuedMessages(newConversationId)

        setMessages((prev) => prev.filter(msg => !msg.id.startsWith('temp-user-')))
        setIsCreatingConversation(false)
      } catch (err: any) {
        const error = new ConversationError(
          ConversationErrorType.CREATE_FAILED,
          err?.message || 'Failed to create conversation',
          true,
          'Failed to create conversation. Please try again.'
        )

        setConversationError(error)
        setError(getErrorUserMessage(error))
        failedMessageRef.current = content
        queueRef.current.clear()
        setIsCreatingConversation(false)
        setMessages((prev) => prev.filter(msg => !msg.id.startsWith('temp-user-')))
      }
    }
  }, [
    activeConversationId,
    setActiveConversation,
    cleanup,
    updateAssistantMessage,
    flushQueuedMessages,
    isCreatingConversation,
    addOptimistic,
    isAuthenticated,
    mounted,
  ])

  /**
   * Clear all messages and reset conversation
   */
  const clearMessages = useCallback(() => {
    cleanup()
    setMessages([])
    setActiveConversation(null)
    setError(null)
    queueRef.current.clear()
  }, [setActiveConversation, cleanup])

  /**
   * Retry failed message
   */
  const retryMessage = useCallback(() => {
    if (failedMessageRef.current) {
      setError(null)
      sendMessage(failedMessageRef.current)
      failedMessageRef.current = null
    }
  }, [sendMessage])

  return {
    messages,
    optimisticMessages,
    isLoading,
    error,
    isOptimistic: isPending || isCreatingConversation,
    sendMessage,
    clearMessages,
    retryMessage,
    activeConversationId,
    errorType: conversationError?.type,
    isRetryable: conversationError?.retryable ?? false,
  }
}
