import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SimpleChat, type Message } from './SimpleChat'
import { useSourcesStore } from '@/lib/stores/sources-store'

vi.mock('@/components/common/KiraLogo', () => ({ KIRAWelcome: () => <div>Welcome</div> }))

const baseMessage: Message = {
  id: 'answer-1',
  role: 'assistant',
  content: 'Answer [source:chunk-2]',
  timestamp: new Date('2026-11-18T00:00:00Z'),
  sources: [{
    id: 'chunk-2',
    chunk_id: 'chunk-2',
    title: 'report.pdf',
    content: 'Evidence',
    score: 0.9,
    document_id: 'doc-1',
    page_number: 3,
  }],
}

beforeEach(() => useSourcesStore.getState().reset())

describe('SimpleChat sources', () => {
  it('opens the selected final citation in the single source store', () => {
    render(<SimpleChat messages={[baseMessage]} isLoading={false} onSendMessage={vi.fn()} onClearChat={vi.fn()} isNewChat={false} activeConversationId="conversation-1" />)

    fireEvent.click(screen.getByRole('button', { name: /chunk-2/ }))
    const sourceState = useSourcesStore.getState()
    expect(sourceState.isOpen).toBe(true)
    expect(sourceState.activeSourceId).toBe('chunk-2')
    expect(sourceState.sources[0].page).toBe(3)
  })

  it('does not expose provisional sources', () => {
    render(<SimpleChat messages={[{ ...baseMessage, provisional: true }]} isLoading={false} onSendMessage={vi.fn()} onClearChat={vi.fn()} isNewChat={false} activeConversationId="conversation-1" />)

    expect(screen.queryByRole('button', { name: /chunk-2/ })).toBeNull()
    expect(useSourcesStore.getState().sources).toHaveLength(0)
  })
})
