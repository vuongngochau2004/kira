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
import { useOptimistic, useTransition } from 'react'
import { MessageQueue, type QueuedMessage } from '@/lib/utils/message-queue'
import type { ThinkingHierarchy } from '@/types/thinking'
import {
  createStreamingStateBuilder,
  parseChunk,
  type MessageState as StreamingMessageState,
  type StreamingState,
  type SourceChunk,
} from '@/lib/streaming'

// ==================== Types ====================

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sources?: SourceChunk[]
  thinkingHierarchy?: ThinkingHierarchy
  streamingState?: StreamingState
  isStreaming?: boolean
  isOptimistic?: boolean
}

// ==================== Constants ====================

// ==================== Helpers ====================

/**
 * Convert StreamingMessageState to ThinkingHierarchy for UI
 * Simple mapping, strip any remaining thinking tags
 */
function stateToHierarchy(state: StreamingMessageState): ThinkingHierarchy {
  const hierarchy: ThinkingHierarchy = {
    status: state.status === 'complete' ? 'complete' : 'running',
    execution: [],
  }

  // Map routing
  if (state.routing) {
    hierarchy.routing = {
      router: state.routing.router,
      intent: state.routing.intent,
      timestamp: state.timestamp,
    }
  }

  // Map retrieval
  if (state.retrieval.length > 0) {
    hierarchy.execution = state.retrieval.map(stage => ({
      stage: 'retrieval',
      iteration: stage.iteration,
      strategy: stage.strategy,
      chunksRetrieved: stage.chunksRetrieved,
      uniqueDocuments: stage.uniqueDocuments,
      topDocuments: stage.topDocuments,
      timestamp: state.timestamp,
    }))
  }

  // Map thinking content - STRIP any remaining thinking tags
  if (state.thinking) {
    // Remove <thinking>, </thinking> tags if present (defense in depth)
    const cleanThinking = state.thinking
      .replace(/<\/?thinking[^>]*>/gi, '')
      .trim()

    hierarchy.reasoning = {
      content: cleanThinking,
      isStreaming: state.status !== 'complete',
      timestamp: state.timestamp,
    }
  }

  return hierarchy
}

// ==================== Custom Hook ====================

export function useSimpleChat() {
  // Store & Router
  const { activeConversationId, setActiveConversation, updateURL } = useConversationStore()
  const { isAuthenticated } = useAuthStore()

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
    loadConversation(activeConversationId)
  }, [activeConversationId, mounted, isAuthenticated, isCreatingConversation])

  useEffect(() => {
    if (!activeConversationId && mounted && isAuthenticated && !isCreatingConversation) {
      setMessages([])
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
    
    // Parse thinking tags from state.content in case the backend sent them in the content stream
    const parsed = parseChunk(state.content, false)
    const hierarchy = stateToHierarchy(state)

    // Merge reasoning extracted from content stream
    const contentReasoning = parsed.reasoning.trim()
    if (contentReasoning) {
      hierarchy.reasoning = {
        content: ((hierarchy.reasoning?.content || '') + '\n' + contentReasoning).trim(),
        isStreaming: state.status !== 'complete',
        timestamp: state.timestamp,
      }
    }

    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === msgId
          ? {
              ...msg,
              content: parsed.content,
              thinkingHierarchy: hierarchy,
              sources: state.sources.length > 0 ? [...state.sources] : undefined,
              streamingState: state.status,
              isStreaming: state.status !== 'complete',
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
            const thinkingData = (msg as any).thinking_data || null
            const isEmptyObject = thinkingData && typeof thinkingData === 'object' && Object.keys(thinkingData).length === 0
            const thinkingMetadata = (isEmptyObject || !thinkingData) ? null : (thinkingData?.thinking || thinkingData)

            const parsed = parseChunk(msg.content || '', false)
            let hierarchy: ThinkingHierarchy | undefined = undefined

            if (thinkingMetadata && typeof thinkingMetadata === 'object') {
              const routerName = thinkingMetadata.router || null
              const retrievalStages = thinkingMetadata.retrieval || []
              let reasoning = thinkingMetadata.reasoning || ''

              if (routerName || retrievalStages.length > 0 || reasoning) {
                hierarchy = {
                  status: 'complete',
                  execution: [],
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
                    stage: 'retrieval',
                    iteration: stage.iteration || 1,
                    strategy: (stage.strategy?.toLowerCase() === 'hybrid' ? 'hybrid' : 'dense') as 'dense' | 'hybrid',
                    chunksRetrieved: stage.chunks_retrieved ?? stage.docs_retrieved ?? 0,
                    uniqueDocuments: stage.unique_documents ?? 1,
                    topDocuments: stage.top_documents,
                    timestamp: new Date(msg.created_at).getTime(),
                  }))
                }

                if (reasoning) {
                  // Strip any <thinking> tags from reasoning content
                  const cleanReasoning = reasoning.replace(/<\/?thinking[^>]*>/gi, '').trim()

                  hierarchy.reasoning = {
                    content: cleanReasoning,
                    isStreaming: false,
                    timestamp: new Date(msg.created_at).getTime(),
                  }
                }
              }
            }

            // Also integrate any thinking tags found in the content itself (defensive fallback)
            const contentReasoning = parsed.reasoning.trim()
            if (contentReasoning) {
              if (!hierarchy) {
                hierarchy = {
                  status: 'complete',
                  execution: [],
                }
              }
              hierarchy.reasoning = {
                content: ((hierarchy.reasoning?.content || '') + '\n' + contentReasoning).trim(),
                isStreaming: false,
                timestamp: new Date(msg.created_at).getTime(),
              }
            }

            return {
              id: msg.id,
              role: 'assistant' as const,
              content: parsed.content || '',
              timestamp: new Date(msg.created_at),
              thinkingHierarchy: hierarchy,
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
              thinkingHierarchy: existingMsg?.thinkingHierarchy || {
                status: 'running',
                execution: [],
              },
              sources: existingMsg?.sources || [],
              streamingState: 'connecting',
              isStreaming: true,
              isOptimistic: false,
            }
          ]
        })

        try {
          const stream = chatAPI.streamMessage(queuedMsg.content, conversationId)

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
          }

          // Mark optimistic messages as real
          setMessages((prev) =>
            prev.map(msg => msg.id.startsWith('temp-')
              ? { ...msg, isOptimistic: false }
              : msg
            )
          )
        } catch (streamErr: any) {
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

        const stream = chatAPI.streamMessage(content.trim(), activeConversationId)

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
        }
      } catch (err: any) {
        if (err.name === 'AbortError') {
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
  }, [setActiveConversation, cleanup])

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
    errorType: conversationError.current?.type,
    isRetryable: conversationError.current?.retryable ?? false,
  }
}
