'use client'

import { useState, useCallback, useRef, useEffect } from 'react'

// Event types matching backend StreamEventTypes
export type StreamEventType =
  | 'thinking_start'
  | 'thinking_progress'
  | 'thinking_end'
  | 'node_start'
  | 'node_end'
  | 'token'
  | 'search'
  | 'source'
  | 'response'
  | 'error'
  | 'done'

export interface StreamEvent {
  type: StreamEventType
  data: {
    timestamp?: number
    token?: string
    node?: string
    query?: string
    results_count?: number
    sources?: SourceChunk[]
    message?: string
  }
}

export interface SourceChunk {
  id: string
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
}

export interface ThinkingStep {
  node: string
  status: 'pending' | 'running' | 'complete'
  duration?: number
  timestamp?: number
}

// Reconnection config
const RETRY_CONFIG = {
  maxRetries: 4,
  baseDelay: 1000,
  maxDelay: 30000,
}

export function useStreamingChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [conversationId, setConversationId] = useState<string>()

  const eventSourceRef = useRef<EventSource | null>(null)
  const currentMessageRef = useRef<string>('')
  const currentThinkingRef = useRef<ThinkingStep[]>([])
  const currentSourcesRef = useRef<SourceChunk[]>([])
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pendingMessageRef = useRef<string>('')
  const retryCountRef = useRef<number>(0)

  // Cleanup function
  const cleanup = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    setIsLoading(false)
  }, [])

  const abortStream = useCallback(() => {
    cleanup()
    retryCountRef.current = 0
    pendingMessageRef.current = ''
  }, [cleanup])

  // Fetch SSE token
  const getSSEToken = useCallback(async (): Promise<string | null> => {
    try {
      const token = localStorage.getItem('access_token')
      if (!token) {
        setError('Không tìm thấy token xác thực')
        return null
      }

      const response = await fetch('/api/v1/chat/sse-token', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error('Failed to get SSE token')
      }

      const data = await response.json()
      return data.token
    } catch (e) {
      console.error('Failed to get SSE token:', e)
      setError('Không thể lấy token SSE')
      return null
    }
  }, [])

  // Reconnection logic
  const reconnect = useCallback(async (content: string, assistantMessageId: string) => {
    const retryCount = retryCountRef.current

    if (retryCount >= RETRY_CONFIG.maxRetries) {
      setError('Mất kết nối sau nhiều lần thử lại')
      setIsLoading(false)
      return
    }

    const delay = Math.min(
      RETRY_CONFIG.baseDelay * Math.pow(2, retryCount),
      RETRY_CONFIG.maxDelay
    )

    console.log(`SSE reconnecting in ${delay}ms... (attempt ${retryCount + 1}/${RETRY_CONFIG.maxRetries})`)

    reconnectTimeoutRef.current = setTimeout(async () => {
      retryCountRef.current = retryCount + 1
      await startStream(content, assistantMessageId)
    }, delay)
  }, [])

  // Start SSE stream
  const startStream = useCallback(async (
    content: string,
    assistantMessageId: string
  ) => {
    const sseToken = await getSSEToken()
    if (!sseToken) {
      setError('Không thể lấy token SSE')
      setIsLoading(false)
      return
    }

    const params = new URLSearchParams({
      message: content,
      temperature: '0.7',
      max_tokens: '2048',
      _: Date.now().toString(),
      sse_token: sseToken,
    })

    if (conversationId) {
      params.append('conversation_id', conversationId)
    }

    const url = `/api/v1/chat/stream?${params.toString()}`
    const eventSource = new EventSource(url)
    eventSourceRef.current = eventSource

    // Reset retry count on successful connection
    eventSource.onopen = () => {
      console.log('SSE connected')
      retryCountRef.current = 0
    }

    eventSource.onmessage = (event) => {
      try {
        const data: StreamEvent = JSON.parse(event.data)
        handleStreamEvent(data, assistantMessageId)
      } catch (e) {
        console.error('Failed to parse SSE event:', e)
      }
    }

    eventSource.onerror = () => {
      console.warn('SSE connection error, attempting reconnect...')
      cleanup()
      reconnect(content, assistantMessageId)
    }
  }, [conversationId, getSSEToken, cleanup, reconnect])

  const handleStreamEvent = useCallback((
    event: StreamEvent,
    messageId: string
  ) => {
    const { type, data } = event

    switch (type) {
      case 'thinking_start':
        currentThinkingRef.current = []
        break

      case 'node_start':
        currentThinkingRef.current = [
          ...currentThinkingRef.current,
          {
            node: data.node || 'unknown',
            status: 'running' as const,
          },
        ]
        updateAssistantMessage(messageId)
        break

      case 'node_end':
        const lastThinking = currentThinkingRef.current[currentThinkingRef.current.length - 1]
        if (lastThinking) {
          lastThinking.status = 'complete'
        }
        updateAssistantMessage(messageId)
        break

      case 'token':
        currentMessageRef.current += data.token || ''
        updateAssistantMessage(messageId)
        break

      case 'source':
        if (data.sources) {
          currentSourcesRef.current = data.sources
          updateAssistantMessage(messageId)
        }
        break

      case 'response':
        if (data.message) {
          currentMessageRef.current = data.message
          updateAssistantMessage(messageId)
        }
        break

      case 'error':
        setError(data.message || 'Đã xảy ra lỗi')
        break

      case 'done':
        cleanup()
        setIsLoading(false)
        break
    }
  }, [cleanup])

  const updateAssistantMessage = useCallback((messageId: string) => {
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === messageId
          ? {
              ...msg,
              content: currentMessageRef.current,
              sources: currentSourcesRef.current.length > 0
                ? [...currentSourcesRef.current]
                : undefined,
              thinking: currentThinkingRef.current.length > 0
                ? [...currentThinkingRef.current]
                : undefined,
            }
          : msg
      )
    )
  }, [])

  const sendMessage = useCallback((content: string) => {
    if (!content.trim()) return

    // Cleanup any existing connection
    abortStream()

    // Reset state
    currentMessageRef.current = ''
    currentThinkingRef.current = []
    currentSourcesRef.current = []
    setError(null)
    setIsLoading(true)
    pendingMessageRef.current = content.trim()

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: content.trim(),
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])

    // Create placeholder assistant message
    const assistantMessageId = (Date.now() + 1).toString()
    setMessages((prev) => [
      ...prev,
      {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
      },
    ])

    // Start stream
    startStream(content.trim(), assistantMessageId)
  }, [abortStream, startStream])

  const clearMessages = useCallback(() => {
    abortStream()
    setMessages([])
    setConversationId(undefined)
    setError(null)
    currentMessageRef.current = ''
    currentThinkingRef.current = []
    currentSourcesRef.current = []
  }, [abortStream])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanup()
    }
  }, [cleanup])

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
    conversationId,
  }
}
