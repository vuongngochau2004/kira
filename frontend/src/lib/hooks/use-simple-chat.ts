'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { conversationsAPI } from '@/lib/api/simple-client'
import { useConversationStore } from '@/lib/stores/conversation-store'
import { useAuthStore } from '@/lib/stores/auth-store'
import type { ThinkingStep, SourceChunk } from '@/components/simple/SimpleChat'

// ==================== Types ====================

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sources?: SourceChunk[]
  thinking?: ThinkingStep[]
  isStreaming?: boolean
  streamingState?: StreamingState
}

export type StreamingState = 'connecting' | 'routing' | 'retrieving' | 'generating' | 'complete' | 'error'

interface StreamingContext {
  state: StreamingState
  router: string
  retrievalStages: string[]
  reasoning: string
  sources: SourceChunk[]
  content: string
  rawContent: string
}

// ==================== Constants ====================

const REASONING_NODE_LABEL = 'Thinking'
const UPDATE_DEBOUNCE_MS = 16 // ~60fps
const STREAM_TIMEOUT_MS = 30000 // 30s timeout

// ==================== Pure Functions ====================

/**
 * Parse thinking tags from raw content
 * Supports <thinking>, , and <suynghi> tags
 */
export function parseThinkingTags(raw: string) {
  const patterns = [
    { start: '<thinking>', end: '</thinking>', startLen: 10 },
    { start: '', end: '</thinkin>', startLen: 7 },
    { start: '<suynghi>', end: '</suynghi>', startLen: 9 },
  ]

  for (const { start, end, startLen } of patterns) {
    const thinkStart = raw.indexOf(start)
    if (thinkStart === -1) continue

    const thinkEnd = raw.indexOf(end)
    if (thinkEnd === -1) {
      // Incomplete thinking tag (still streaming)
      const reasoning = raw.slice(thinkStart + startLen)
      const cleanReasoning = stripPartialClosingTag(reasoning)

      return {
        reasoning: cleanReasoning,
        content: raw.slice(0, thinkStart),
        isThinkingComplete: false,
        hasThinking: true,
      }
    }

    const reasoning = raw.slice(thinkStart + startLen, thinkEnd)
    const afterThink = raw.slice(thinkEnd + end.length)

    return {
      reasoning,
      content: raw.slice(0, thinkStart) + afterThink,
      isThinkingComplete: true,
      hasThinking: true,
    }
  }

  return {
    reasoning: '',
    content: raw,
    isThinkingComplete: true,
    hasThinking: false,
  }
}

/**
 * Strip partial closing tag from reasoning text
 */
function stripPartialClosingTag(text: string): string {
  const patterns = [
    /<\/t?h?i?n?k?i?n?g?>?$/i,
    /<\/t?h?i?n?k?>?$/i,
    /<\/s?u?y?n?g?h?i?>?$/i,
  ]

  for (const pattern of patterns) {
    const match = text.match(pattern)
    if (match) {
      return text.substring(0, match.index)
    }
  }
  return text
}

/**
 * Build thinking node from streaming context
 */
function buildThinkingNode(ctx: StreamingContext, isComplete: boolean): ThinkingStep | null {
  if (!ctx.router && ctx.retrievalStages.length === 0 && !ctx.reasoning) {
    return null
  }

  let nodeContent = ctx.router

  if (ctx.retrievalStages.length > 0) {
    nodeContent += '\n  ↳ Tool Call: Retrieval'
    ctx.retrievalStages.forEach((stage) => {
      nodeContent += `\n    • ${stage}`
    })
  }

  if (ctx.reasoning) {
    nodeContent += `\n  ↳ LLM Reasoning:${ctx.reasoning.split('\n').map((line) => `  ${line}`).join('\n')}`
  }

  return {
    node: nodeContent,
    status: isComplete ? 'complete' : 'running',
  }
}

// ==================== Custom Hook ====================

export function useSimpleChat() {
  // ==================== Store & Router ====================
  const { activeConversationId, setActiveConversation } = useConversationStore()
  const { isAuthenticated } = useAuthStore()
  const router = useRouter()

  // ==================== State ====================
  const [mounted, setMounted] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // ==================== Refs ====================
  const abortControllerRef = useRef<AbortController | null>(null)
  const streamingCtxRef = useRef<StreamingContext>({
    state: 'connecting',
    router: '',
    retrievalStages: [],
    reasoning: '',
    sources: [],
    content: '',
    rawContent: '',
  })
  const assistantMsgIdRef = useRef<string | null>(null)
  const pendingConversationIdRef = useRef<string | null>(null)
  const updateTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

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
    if (activeConversationId && mounted && isAuthenticated) {
      loadConversation(activeConversationId)
    } else {
      setMessages([])
    }
  }, [activeConversationId, mounted, isAuthenticated])

  // ==================== Helpers ====================

  /**
   * Reset streaming context to initial state
   */
  const resetStreamingContext = useCallback(() => {
    streamingCtxRef.current = {
      state: 'connecting',
      router: '',
      retrievalStages: [],
      reasoning: '',
      sources: [],
      content: '',
      rawContent: '',
    }
  }, [])

  /**
   * Cleanup stream and reset state
   */
  const cleanup = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    if (updateTimerRef.current) {
      clearTimeout(updateTimerRef.current)
      updateTimerRef.current = null
    }
    resetStreamingContext()
    assistantMsgIdRef.current = null
    pendingConversationIdRef.current = null
    setIsLoading(false)
  }, [resetStreamingContext])

  /**
   * Debounced message update to reduce re-renders
   */
  const scheduleUpdate = useCallback((updater: () => void) => {
    if (updateTimerRef.current) {
      clearTimeout(updateTimerRef.current)
    }
    updateTimerRef.current = setTimeout(() => {
      updater()
      updateTimerRef.current = null
    }, UPDATE_DEBOUNCE_MS)
  }, [])

  /**
   * Update assistant message with current streaming context
   */
  const updateAssistantMessage = useCallback((isComplete: boolean = false) => {
    const msgId = assistantMsgIdRef.current
    if (!msgId) return

    const ctx = streamingCtxRef.current
    const { reasoning, content, isThinkingComplete } = parseThinkingTags(ctx.rawContent)

    ctx.content = content
    ctx.reasoning = reasoning

    const thinkingNode = buildThinkingNode(ctx, isComplete && isThinkingComplete)

    scheduleUpdate(() => {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === msgId
            ? {
                ...msg,
                content: ctx.content,
                thinking: thinkingNode ? [thinkingNode] : undefined,
                sources: ctx.sources.length > 0 ? [...ctx.sources] : undefined,
                streamingState: ctx.state,
                isStreaming: !isComplete,
              }
            : msg
        )
      )
    })
  }, [scheduleUpdate])

  /**
   * Load conversation from API
   */
  const loadConversation = async (id: string) => {
    try {
      const conversation = await conversationsAPI.get(id)
      setMessages(
        conversation.messages.map((msg) => {
          if (msg.role === 'assistant') {
            const { reasoning, content } = parseThinkingTags(msg.content)
            const thinkingMetadata = (msg.metadata as any)?.thinking || null

            let existingThinking: ThinkingStep[] = []

            if (thinkingMetadata && typeof thinkingMetadata === 'object') {
              const routerName = thinkingMetadata.router || null
              const retrievalStages = thinkingMetadata.retrieval || []

              if (routerName) {
                let nodeContent = routerName

                if (retrievalStages.length > 0) {
                  nodeContent += '\n  ↳ Tool Call: Retrieval'
                  retrievalStages.forEach((stage: any) => {
                    const iteration = stage.iteration || 1
                    const strategy = stage.strategy || 'Hybrid'
                    const docsCount = stage.docs_retrieved || 0
                    nodeContent += `\n    • Iteration ${iteration}, Strategy: ${strategy}, Retrieved: ${docsCount} docs`
                  })
                }

                if (reasoning) {
                  nodeContent += `\n  ↳ LLM Reasoning:${reasoning.split('\n').map((line: string) => `${line}`).join('\n')}`
                }

                existingThinking = [
                  {
                    node: nodeContent,
                    status: 'complete' as const,
                  }
                ]
              }
            }

            return {
              id: msg.id,
              role: 'assistant' as const,
              content: content,
              timestamp: new Date(msg.created_at),
              thinking: existingThinking.length > 0 ? existingThinking : undefined,
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
   * Send message and handle streaming response
   */
  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return

    cleanup()
    setError(null)
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
      thinking: [],
      sources: [],
      streamingState: 'connecting',
      isStreaming: true,
    }

    setMessages((prev) => [...prev, userMessage, assistantMessage])

    try {
      const { chatAPI } = await import('@/lib/api/simple-client')
      const stream = chatAPI.streamMessage(content.trim(), activeConversationId || undefined)

      // Stream timeout
      const timeoutId = setTimeout(() => {
        if (abortControllerRef.current) {
          abortControllerRef.current.abort()
          setError('Streaming timeout - please try again')
        }
      }, STREAM_TIMEOUT_MS)

      for await (const chunk of stream) {
        const { type, data: eventData } = chunk
        const ctx = streamingCtxRef.current

        switch (type) {
          case 'routing':
            ctx.state = 'routing'
            ctx.router = `${eventData?.router || 'Routing'}${eventData?.intent ? ` (${eventData.intent})` : ''}`
            updateAssistantMessage(false)
            break

          case 'retrieval':
            ctx.state = 'retrieving'
            const iteration = eventData?.iteration || 1
            const strategy = eventData?.strategy || 'Hybrid'
            const docsCount = eventData?.docs_retrieved || 0
            ctx.retrievalStages.push(
              `Iteration ${iteration}, Strategy: ${strategy}, Retrieved: ${docsCount} docs`
            )
            updateAssistantMessage(false)
            break

          case 'content':
            ctx.state = 'generating'
            ctx.rawContent += eventData?.text || ''
            updateAssistantMessage(false)
            break

          case 'metadata':
            if (eventData?.citations) {
              ctx.sources = eventData.citations
            } else if (eventData?.sources) {
              ctx.sources = eventData.sources
            }

            if (eventData?.conversation_id && !activeConversationId) {
              pendingConversationIdRef.current = eventData.conversation_id
              setActiveConversation(eventData.conversation_id)
            }
            break

          case 'done':
            clearTimeout(timeoutId)
            ctx.state = 'complete'
            updateAssistantMessage(true)
            setIsLoading(false)

            if (pendingConversationIdRef.current && !activeConversationId) {
              router.push(`/conversation/${pendingConversationIdRef.current}`)
              pendingConversationIdRef.current = null
            }
            break

          case 'error':
            clearTimeout(timeoutId)
            ctx.state = 'error'
            updateAssistantMessage(true)
            setError(eventData?.error || 'Streaming error occurred')
            setIsLoading(false)
            break
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        // User cancelled - silent fail
      } else {
        const errorMsg = err?.message || 'Failed to send message'
        setError(errorMsg)
        streamingCtxRef.current.state = 'error'
        updateAssistantMessage(true)
      }
    } finally {
      setIsLoading(false)
      abortControllerRef.current = null
    }
  }, [activeConversationId, setActiveConversation, router, cleanup, updateAssistantMessage, isAuthenticated, mounted])

  /**
   * Clear all messages and reset conversation
   */
  const clearMessages = useCallback(() => {
    cleanup()
    setMessages([])
    setActiveConversation(null)
    setError(null)
  }, [setActiveConversation, cleanup])

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
    activeConversationId,
  }
}
