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

const REASONING_NODE_LABEL = 'Thinking'

export function parseThinkingTags(raw: string) {
  let thinkStart = raw.indexOf('<thinking>')
  let tagLen = 10
  let closeTag = '</thinking>'

  if (thinkStart === -1) {
    thinkStart = raw.indexOf('<think>')
    tagLen = 7
    closeTag = '</think>'
  }

  if (thinkStart === -1) {
    thinkStart = raw.indexOf('<suynghi>')
    tagLen = 9
    closeTag = '</suynghi>'
  }

  if (thinkStart === -1) {
    return {
      reasoning: '',
      content: raw,
      isThinkingComplete: true,
      hasThinking: false,
    }
  }

  const thinkEnd = raw.indexOf(closeTag)
  if (thinkEnd === -1) {
    // Thẻ think chưa được đóng (đang stream)
    const reasoning = raw.slice(thinkStart + tagLen)
    
    // Strip partial closing tag from reasoning if present
    let cleanReasoning = reasoning
    const matchEnd = closeTag === '</thinking>'
      ? reasoning.match(/<\/t?h?i?n?k?i?n?g?>?$/i)
      : closeTag === '</think>'
      ? reasoning.match(/<\/t?h?i?n?k?>?$/i)
      : reasoning.match(/<\/s?u?y?n?g?h?i?>?$/i)
      
    if (matchEnd) {
      cleanReasoning = reasoning.substring(0, matchEnd.index)
    }

    return {
      reasoning: cleanReasoning,
      content: raw.slice(0, thinkStart),
      isThinkingComplete: false,
      hasThinking: true,
    }
  }

  // Thẻ think đã được đóng hoàn toàn
  const reasoning = raw.slice(thinkStart + tagLen, thinkEnd)
  const afterThink = raw.slice(thinkEnd + closeTag.length)
  return {
    reasoning,
    content: raw.slice(0, thinkStart) + afterThink,
    isThinkingComplete: true,
    hasThinking: true,
  }
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
  const currentRawContentRef = useRef<string>('')
  const currentActiveRouterRef = useRef<string>('')
  const retrievalStagesRef = useRef<string[]>([])
  const currentThoughtsRef = useRef<string>('')

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
        conversation.messages.map((msg) => {
          if (msg.role === 'assistant') {
            const { reasoning, content } = parseThinkingTags(msg.content)
            let existingThinking = (msg.metadata as any)?.thinking || []
            
            // Detect if we already have a unified hierarchical node
            const hasUnifiedNode = existingThinking.some((step: any) => step.node.includes('↳'))

            if (reasoning && !hasUnifiedNode) {
              const routerStep = existingThinking.find(
                (step: any) => !step.node.includes('Thinking') && !step.node.includes('Retrieval')
              )
              const routerName = routerStep ? routerStep.node : 'Thinking'
              
              const retrievalSteps = existingThinking.filter(
                (step: any) => step.node.includes('Retrieval')
              )

              let nodeContent = routerName
              if (retrievalSteps.length > 0) {
                nodeContent += '\n  ↳ Tool Call: Retrieval'
                retrievalSteps.forEach((step: any) => {
                  const cleanDesc = step.node.replace(/Retrieval Stage\s*/i, '')
                  nodeContent += `\n    • ${cleanDesc}`
                })
              }

              nodeContent += `\n  ↳ LLM Reasoning:${reasoning.split('\n').map((line: string) => `    ${line}`).join('\n')}`

              existingThinking = [
                {
                  node: nodeContent,
                  status: 'complete' as const,
                }
              ]
            }

            return {
              id: msg.id,
              role: 'assistant' as const,
              content: content,
              timestamp: new Date(msg.created_at),
              thinking: existingThinking.length > 0 ? existingThinking : undefined,
              sources: msg.sources || (msg.metadata as any)?.sources || undefined,
            }
          }

          return {
            id: msg.id,
            role: 'user' as const,
            content: msg.content,
            timestamp: new Date(msg.created_at),
          }
        })
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
    currentRawContentRef.current = ''
    currentActiveRouterRef.current = ''
    retrievalStagesRef.current = []
    currentThoughtsRef.current = ''

    const updateMessage = (updates: Partial<Message>) => {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId ? { ...msg, ...updates } : msg
        )
      )
    }

    const updateThinkingState = (isComplete: boolean) => {
      const routerName = currentActiveRouterRef.current || 'Thinking'
      
      let nodeContent = routerName
      
      if (retrievalStagesRef.current.length > 0) {
        nodeContent += '\n  ↳ Tool Call: Retrieval'
        retrievalStagesRef.current.forEach((stage) => {
          nodeContent += `\n    • ${stage}`
        })
      }
      
      if (currentThoughtsRef.current) {
        nodeContent += `\n  ↳ LLM Reasoning:${currentThoughtsRef.current.split('\n').map(line => `    ${line}`).join('\n')}`
      }

      currentThinkingRef.current = [
        {
          node: nodeContent,
          status: (isComplete ? 'complete' : 'running') as 'complete' | 'running',
        }
      ]

      updateMessage({ thinking: [...currentThinkingRef.current] })
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

              // Support new structured event system: { type: string, data?: any }
              if (parsed.type !== undefined) {
                const { type, data: eventData } = parsed

                if (type === 'content') {
                  currentRawContentRef.current += eventData?.text || ''
                  const { reasoning, content, isThinkingComplete, hasThinking } = parseThinkingTags(currentRawContentRef.current)
                  currentContentRef.current = content
                  if (hasThinking) {
                    currentThoughtsRef.current = reasoning
                    updateThinkingState(isThinkingComplete)
                    updateMessage({ content: currentContentRef.current })
                  } else {
                    updateMessage({ content: currentContentRef.current })
                  }
                } else if (type === 'routing') {
                  const routerName = eventData?.router || 'Routing'
                  const intent = eventData?.intent ? ` (${eventData.intent})` : ''
                  const fullRouterName = `${routerName}${intent}`
                  currentActiveRouterRef.current = fullRouterName
                  updateThinkingState(false)
                } else if (type === 'retrieval') {
                  const iteration = eventData?.iteration || 1
                  const strategy = eventData?.strategy || 'Hybrid'
                  const docsCount = eventData?.docs_retrieved || 0
                  retrievalStagesRef.current.push(
                    `Iteration ${iteration}, Strategy: ${strategy}, Retrieved: ${docsCount} docs`
                  )
                  updateThinkingState(false)
                } else if (type === 'metadata') {
                  if (eventData?.citations !== undefined) {
                    currentSourcesRef.current = eventData.citations
                    updateMessage({ sources: [...currentSourcesRef.current] })
                  } else if (eventData?.sources !== undefined) {
                    currentSourcesRef.current = eventData.sources
                    updateMessage({ sources: [...currentSourcesRef.current] })
                  }

                  if (eventData?.conversation_id !== undefined) {
                    if (!activeConversationId) {
                      setActiveConversation(eventData.conversation_id)
                      router.push(`/conversation/${eventData.conversation_id}`)
                    }
                  }
                } else if (type === 'done') {
                  updateThinkingState(true)
                  setIsLoading(false)
                } else if (type === 'error') {
                  setError(eventData?.error || 'Đã xảy ra lỗi khi tải luồng dữ liệu')
                  setIsLoading(false)
                }
              } else {
                // Backward-compatible legacy events
                if (parsed.token !== undefined) {
                  currentRawContentRef.current += parsed.token
                  const { reasoning, content, isThinkingComplete, hasThinking } = parseThinkingTags(currentRawContentRef.current)
                  currentContentRef.current = content
                  if (hasThinking) {
                    currentThoughtsRef.current = reasoning
                    updateThinkingState(isThinkingComplete)
                    updateMessage({ content: currentContentRef.current })
                  } else {
                    updateMessage({ content: currentContentRef.current })
                  }
                } else if (parsed.content !== undefined && typeof parsed.content === 'string') {
                  currentRawContentRef.current += parsed.content
                  const { reasoning, content, isThinkingComplete, hasThinking } = parseThinkingTags(currentRawContentRef.current)
                  currentContentRef.current = content
                  if (hasThinking) {
                    currentThoughtsRef.current = reasoning
                    updateThinkingState(isThinkingComplete)
                    updateMessage({ content: currentContentRef.current })
                  } else {
                    updateMessage({ content: currentContentRef.current })
                  }
                } else if (parsed.message !== undefined && typeof parsed.message === 'string') {
                  currentRawContentRef.current = parsed.message
                  const { reasoning, content, isThinkingComplete, hasThinking } = parseThinkingTags(currentRawContentRef.current)
                  currentContentRef.current = content
                  if (hasThinking) {
                    currentThoughtsRef.current = reasoning
                    updateThinkingState(isThinkingComplete)
                    updateMessage({ content: currentContentRef.current })
                  } else {
                    updateMessage({ content: currentContentRef.current })
                  }
                } else if (parsed.node !== undefined) {
                  const nodeName = parsed.node || 'unknown'
                  if (nodeName.toLowerCase().includes('retrieval')) {
                    retrievalStagesRef.current.push(nodeName)
                  } else {
                    currentActiveRouterRef.current = nodeName
                  }
                  updateThinkingState(false)
                } else if (parsed.sources !== undefined) {
                  currentSourcesRef.current = parsed.sources
                  updateMessage({ sources: [...currentSourcesRef.current] })
                } else if (parsed.timestamp && Object.keys(parsed).length === 1) {
                  updateThinkingState(true)
                } else if (parsed.conversation_id !== undefined) {
                  if (!activeConversationId) {
                    setActiveConversation(parsed.conversation_id)
                    router.push(`/conversation/${parsed.conversation_id}`)
                  }
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
