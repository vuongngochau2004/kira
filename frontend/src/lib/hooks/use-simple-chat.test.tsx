import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { chatAPI, conversationsAPI } from '@/lib/api/simple-client'
import { useAuthStore } from '@/lib/stores/auth-store'
import { useConversationStore } from '@/lib/stores/conversation-store'
import { useSimpleChat } from './use-simple-chat'

vi.mock('@/lib/api/simple-client', () => ({
  chatAPI: { streamMessage: vi.fn() },
  conversationsAPI: { create: vi.fn(), get: vi.fn() },
}))

beforeEach(() => {
  useConversationStore.setState({ activeConversationId: null })
  useAuthStore.setState({ isAuthenticated: true })
  vi.mocked(conversationsAPI.create).mockReset()
  vi.mocked(conversationsAPI.get).mockReset()
  vi.mocked(chatAPI.streamMessage).mockReset()
})

afterEach(() => {
  useConversationStore.setState({ activeConversationId: null })
  useAuthStore.setState({ isAuthenticated: false })
})

describe('useSimpleChat first conversation', () => {
  it('stops a first message while conversation creation is pending', async () => {
    const conversation = {
      id: 'conversation-1', user_id: 'user-1', title: null, source: 'web',
      status: 'active', created_at: '', updated_at: '', messages: [],
    }
    let resolveCreate: (value: typeof conversation) => void = () => undefined
    vi.mocked(conversationsAPI.create).mockImplementation(() => new Promise((resolve) => {
      resolveCreate = resolve
    }))
    vi.mocked(conversationsAPI.get).mockResolvedValue(conversation)

    const { result } = renderHook(() => useSimpleChat())
    act(() => { void result.current.sendMessage('Question') })
    await waitFor(() => expect(result.current.isLoading).toBe(true))

    act(() => result.current.stopGenerating())
    expect(result.current.isLoading).toBe(false)
    expect(result.current.messages.find((message) => message.role === 'assistant')?.streamingState).toBe('stopped')
    expect(result.current.messages.find((message) => message.role === 'user')?.unsaved).toBe(true)

    await act(async () => { resolveCreate(conversation) })
    expect(chatAPI.streamMessage).not.toHaveBeenCalled()
    expect(result.current.messages.find((message) => message.role === 'assistant')?.streamingState).toBe('stopped')
  })

  it('keeps its local first answer and only reloads later conversation switches', async () => {
    const conversation = {
      id: 'conversation-1', user_id: 'user-1', title: null, source: 'web',
      status: 'active', created_at: '', updated_at: '',
    }
    vi.mocked(conversationsAPI.create).mockResolvedValue(conversation)
    vi.mocked(conversationsAPI.get).mockImplementation(async (id) => ({
      ...conversation,
      id,
      messages: [{
        id: `saved-${id}`, conversation_id: id, role: 'assistant',
        content: `Saved ${id}`, metadata: {}, created_at: new Date().toISOString(),
      }],
    }))
    vi.mocked(chatAPI.streamMessage).mockImplementation(async function* () {
      yield { type: 'content', data: { text: 'Draft', provisional: true, attempt: 1 } }
      yield { type: 'content_replace', data: { text: 'Final', provisional: false } }
      yield { type: 'metadata', data: { citations: [] } }
      yield { type: 'done', data: undefined }
    })

    const { result } = renderHook(() => useSimpleChat())
    await act(async () => { await result.current.sendMessage('Question') })
    await waitFor(() => expect(result.current.messages.some((message) => message.content === 'Final')).toBe(true))
    expect(result.current.messages.find((message) => message.role === 'user')?.unsaved).toBe(false)
    expect(conversationsAPI.get).not.toHaveBeenCalled()

    act(() => useConversationStore.getState().setActiveConversation('conversation-2'))
    await waitFor(() => expect(conversationsAPI.get).toHaveBeenCalledWith('conversation-2'))
    await waitFor(() => expect(result.current.messages[0]?.content).toBe('Saved conversation-2'))

    act(() => useConversationStore.getState().setActiveConversation('conversation-1'))
    await waitFor(() => expect(conversationsAPI.get).toHaveBeenCalledWith('conversation-1'))
  })

  it('marks the stopped prompt and preview as unsaved before metadata', async () => {
    const conversation = {
      id: 'conversation-1', user_id: 'user-1', title: null, source: 'web',
      status: 'active', created_at: '', updated_at: '', messages: [],
    }
    useConversationStore.setState({ activeConversationId: conversation.id })
    vi.mocked(conversationsAPI.get).mockResolvedValue(conversation)
    vi.mocked(chatAPI.streamMessage).mockImplementation((_message, _conversationId, signal) => (
      async function* () {
        yield { type: 'content' as const, data: { text: 'Draft', provisional: true, attempt: 1 } }
        await new Promise<void>((resolve) => {
          if (signal?.aborted) resolve()
          else signal?.addEventListener('abort', () => resolve(), { once: true })
        })
      }
    )())

    const { result } = renderHook(() => useSimpleChat())
    await waitFor(() => expect(conversationsAPI.get).toHaveBeenCalledWith(conversation.id))
    act(() => { void result.current.sendMessage('Question') })
    await waitFor(() => expect(result.current.messages.some((message) => message.content === 'Draft')).toBe(true))

    act(() => result.current.stopGenerating())
    await waitFor(() => expect(result.current.messages.find((message) => message.role === 'assistant')?.streamingState).toBe('stopped'))
    expect(result.current.messages.find((message) => message.role === 'user')?.unsaved).toBe(true)
    expect(result.current.messages.find((message) => message.role === 'assistant')).toMatchObject({
      content: 'Draft', provisional: true,
    })
  })
})
