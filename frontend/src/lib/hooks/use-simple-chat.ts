'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { conversationsAPI } from '@/lib/api/simple-client'
import { useConversationStore } from '@/lib/stores/conversation-store'
import { useAuthStore } from '@/lib/stores/auth-store'
import type { ThinkingStep, SourceChunk } from '@/components/simple/SimpleChat'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sources?: SourceChunk[]
  thinking?: ThinkingStep[]
}

export function useSimpleChat() {
  const { activeConversationId, setActiveConversation } = useConversationStore()
  const { isAuthenticated } = useAuthStore()
  const router = useRouter()
  const [mounted, setMounted] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const abortControllerRef = useRef<AbortController | null>(null)
  const currentThinkingRef = useRef<ThinkingStep[]>([])
  const currentSourcesRef = useRef<SourceChunk[]>([])
  const currentContentRef = useRef<string>('')

  useEffect(() => {
    setMounted(true)
  }, [])

  const cleanupStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setIsLoading(false)
  }, [])

  useEffect(() => {
    return () => {
      cleanupStream()
    }
  }, [cleanupStream])

  useEffect(() => {
    if (activeConversationId && mounted && isAuthenticated) {
      loadConversation(activeConversationId)
    } else {
      setMessages([])
    }
  }, [activeConversationId, mounted, isAuthenticated])

  const loadConversation = async (id: string) => {
    try {
      const conversation = await conversationsAPI.get(id)
      setMessages(
        conversation.messages.map((msg) => ({
          id: msg.id,
          role: msg.role as 'user' | 'assistant',
          content: msg.content,
          timestamp: new Date(msg.created_at),
          thinking: (msg.metadata as any)?.thinking || undefined,
          sources: (msg.metadata as any)?.sources || undefined,
        }))
      )
    } catch (err) {
      console.error('Failed to load conversation:', err)
    }
  }

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return

    cleanupStream()
    setError(null)
    setIsLoading(true)

    const userMessageId = Date.now().toString()
    const assistantMessageId = (Date.now() + 1).toString()

    const userMessage: Message = {
      id: userMessageId,
      role: 'user',
      content: content.trim(),
      timestamp: new Date(),
    }

    const assistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      thinking: [],
      sources: [],
    }

    setMessages((prev) => [...prev, userMessage, assistantMessage])

    // Reset refs
    currentThinkingRef.current = []
    currentSourcesRef.current = []
    currentContentRef.current = ''

    const updateMessage = (updates: Partial<Message>) => {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId ? { ...msg, ...updates } : msg
        )
      )
    }

    try {
      const token = localStorage.getItem('access_token')

      // Use relative path — Next.js rewrites /api/* to backend (avoids CORS)
      const apiBase = ''

      // Build stream URL with query params (backend expects query parameters)
      const params = new URLSearchParams({
        message: content.trim(),
        temperature: '0.7',
        max_tokens: '2048',
      })

      if (activeConversationId) {
        params.append('conversation_id', activeConversationId)
      }

      const streamUrl = `${apiBase}/api/v1/chat/stream?${params.toString()}`

      // Use fetch with streaming reader
      const abortController = new AbortController()
      abortControllerRef.current = abortController

      const headers: Record<string, string> = {}
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      const response = await fetch(streamUrl, {
        method: 'POST',
        headers,
        signal: abortController.signal,
      })

      if (!response.ok) throw new Error(`Stream error: ${response.status}`)


      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()

        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Process complete SSE messages
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim()

            if (data === '[DONE]') {
              setIsLoading(false)
              break
            }

            try {
              const parsed = JSON.parse(data)

              // Handle different event types based on data structure
              if (parsed.token !== undefined) {
                // Token event
                currentContentRef.current += parsed.token
                updateMessage({ content: currentContentRef.current })
              } else if (parsed.content !== undefined && typeof parsed.content === 'string') {
                // Content event from backend
                currentContentRef.current += parsed.content
                updateMessage({ content: currentContentRef.current })
              } else if (parsed.message !== undefined && typeof parsed.message === 'string') {
                // Response event (full message)
                currentContentRef.current = parsed.message
                updateMessage({ content: currentContentRef.current })
              } else if (parsed.node !== undefined) {
                // Node start event
                currentThinkingRef.current = [
                  ...currentThinkingRef.current,
                  {
                    node: parsed.node || 'unknown',
                    status: 'running' as const,
                    timestamp: parsed.timestamp,
                  },
                ]
                updateMessage({ thinking: [...currentThinkingRef.current] })
              } else if (parsed.sources !== undefined) {
                // Source event
                currentSourcesRef.current = parsed.sources
                updateMessage({ sources: [...currentSourcesRef.current] })
              } else if (parsed.timestamp && Object.keys(parsed).length === 1) {
                // Node end event (just timestamp)
                if (currentThinkingRef.current.length > 0) {
                  const lastIndex = currentThinkingRef.current.length - 1
                  currentThinkingRef.current[lastIndex] = {
                    ...currentThinkingRef.current[lastIndex],
                    status: 'complete' as const,
                  }
                  updateMessage({ thinking: [...currentThinkingRef.current] })
                }
              } else if (parsed.conversation_id !== undefined) {
                // Conversation event
                if (!activeConversationId) {
                  setActiveConversation(parsed.conversation_id)
                  router.push(`/conversation/${parsed.conversation_id}`)
                }
              }
            } catch (e) {
              // Ignore parse errors for non-JSON lines
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('Stream aborted')
      } else {
        const errorMsg = err?.message || 'Đã xảy ra lỗi khi gửi tin nhắn'
        setError(errorMsg)
        console.error('Stream error:', err)
      }
    } finally {
      setIsLoading(false)
      abortControllerRef.current = null
    }
  }, [activeConversationId, setActiveConversation, router, cleanupStream, isAuthenticated, mounted])

  const clearMessages = useCallback(() => {
    cleanupStream()
    setMessages([])
    setActiveConversation(null)
    setError(null)
  }, [setActiveConversation, cleanupStream])

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
    activeConversationId,
  }
}
