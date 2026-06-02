'use client'

import { useEffect, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useConversationStore } from '@/lib/stores/conversation-store'
import { SimpleChat } from '@/components/simple/SimpleChat'
import { useSimpleChat } from '@/lib/hooks/use-simple-chat'
import { AuthGuard } from '@/components/auth/auth-guard'

export default function ConversationPage() {
  const params = useParams()
  const router = useRouter()
  const { setActiveConversation, clearActiveConversation } = useConversationStore()
  const chat = useSimpleChat()
  const prevIdRef = useRef<string | null>(null)

  useEffect(() => {
    const conversationId = params.id as string

    // Validate conversation ID (UUID v4 format)
    if (!conversationId || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(conversationId)) {
      router.push('/chat')
      return
    }

    if (conversationId) {
      setActiveConversation(conversationId)
      // Store in ref for cleanup comparison
      if (prevIdRef.current !== conversationId) {
        prevIdRef.current = conversationId
      }
    }

    return () => {
      // Only clear if ID actually changed (not just auth state change)
      if (prevIdRef.current && prevIdRef.current !== conversationId) {
        clearActiveConversation()
        prevIdRef.current = null
      }
    }
  }, [params.id, router, setActiveConversation, clearActiveConversation])

  return (
    <AuthGuard>
      <div className="h-full flex flex-col overflow-hidden bg-background min-h-0">
        <SimpleChat
          messages={chat.messages}
          isLoading={chat.isLoading}
          onSendMessage={chat.sendMessage}
          onClearChat={chat.clearMessages}
          error={chat.error}
          className="flex-1"
          isNewChat={false}
        />
      </div>
    </AuthGuard>
  )
}
