'use client'

import { useEffect } from 'react'
import { useSimpleChat } from '@/lib/hooks/use-simple-chat'
import { useConversationStore } from '@/lib/stores/conversation-store'
import { SimpleChat } from '@/components/simple/SimpleChat'
import { AuthGuard } from '@/components/auth/auth-guard'

export default function ChatPage() {
  const chat = useSimpleChat()
  const { setActiveConversation } = useConversationStore()

  useEffect(() => {
    // Clear active conversation on new chat
    setActiveConversation(null)
  }, [setActiveConversation])

  return (
    <AuthGuard>
      <div className="h-full flex flex-col overflow-hidden bg-background min-h-0">
        <SimpleChat
          messages={chat.messages}
          isLoading={chat.isLoading}
          onSendMessage={chat.sendMessage}
          onClearChat={chat.clearMessages}
          error={chat.error}
          isNewChat={true}
        />
      </div>
    </AuthGuard>
  )
}
