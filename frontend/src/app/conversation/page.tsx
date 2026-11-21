'use client'

import { Suspense, useEffect, useRef } from 'react'
import { useSearchParams } from 'next/navigation'
import { useChat } from '@/features/chat/hooks/use-chat'
import { useConversationStore } from '@/features/chat/stores/conversation-store'
import { useSourcesStore } from '@/features/chat/stores/sources-store'
import { ChatView } from '@/features/chat/components/ChatView'
import { AuthGuard } from '@/features/auth/components/AuthGuard'
import { isValidUUID } from '@/lib/utils/uuid'

function ConversationContent() {
  const searchParams = useSearchParams()
  const conversationId = searchParams.get('id')
  const chat = useChat()
  const { syncFromURL, isLoading: storeLoading } = useConversationStore()
  const resetSources = useSourcesStore((state) => state.reset)
  const prevConversationIdRef = useRef<string | null | undefined>(undefined)

  // Sync conversation state from URL
  const isNewChat = !conversationId || !isValidUUID(conversationId)

  useEffect(() => {
    if (isNewChat) {
      resetSources()
    }
  }, [isNewChat, resetSources])

  // FIX: Smooth URL sync without jarring re-render
  useEffect(() => {
    // Only sync if conversationId actually changed (not just on mount)
    if (conversationId !== prevConversationIdRef.current) {
      syncFromURL(conversationId)
      prevConversationIdRef.current = conversationId
    }
  }, [conversationId, syncFromURL])

  return (
    <div className="h-full flex flex-col overflow-hidden bg-background min-h-0">
      <ChatView
        messages={chat.messages}
        optimisticMessages={chat.optimisticMessages}
        isLoading={chat.isLoading || storeLoading}
        isOptimistic={chat.isOptimistic}
        onSendMessage={chat.sendMessage}
        onStopGenerating={chat.stopGenerating}
        onClearChat={chat.clearMessages}
        error={chat.error}
        retryMessage={chat.retryMessage}
        isRetryable={chat.isRetryable}
        errorType={chat.errorType}
        activeConversationId={isNewChat ? null : conversationId}
        isNewChat={isNewChat}
      />
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  )
}

export default function ConversationPage() {
  return (
    <AuthGuard>
      <Suspense fallback={<LoadingSkeleton />}>
        <ConversationContent />
      </Suspense>
    </AuthGuard>
  )
}
