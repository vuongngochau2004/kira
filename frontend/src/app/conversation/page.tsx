'use client'

import { Suspense, useEffect, useRef } from 'react'
import { useSearchParams } from 'next/navigation'
import { useSimpleChat } from '@/lib/hooks/use-simple-chat'
import { useConversationStore } from '@/lib/stores/conversation-store'
import { SimpleChat } from '@/components/simple/SimpleChat'
import { AuthGuard } from '@/components/auth/auth-guard'
import { isValidUUID } from '@/lib/utils/uuid'

function ConversationContent() {
  const searchParams = useSearchParams()
  const conversationId = searchParams.get('id')
  const chat = useSimpleChat()
  const { syncFromURL, isLoading: storeLoading } = useConversationStore()
  const prevConversationIdRef = useRef<string | null>(null)

  // Sync conversation state from URL
  const isNewChat = !conversationId || !isValidUUID(conversationId)

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
      <SimpleChat
        messages={chat.messages}
        optimisticMessages={chat.optimisticMessages}
        isLoading={chat.isLoading || storeLoading}
        isOptimistic={chat.isOptimistic}
        onSendMessage={chat.sendMessage}
        onClearChat={chat.clearMessages}
        error={chat.error}
        retryMessage={chat.retryMessage}
        isRetryable={chat.isRetryable}
        errorType={chat.errorType}
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
