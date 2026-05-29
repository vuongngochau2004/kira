'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useSimpleChat } from '@/lib/hooks/use-simple-chat'
import { useConversationStore } from '@/lib/stores/conversation-store'
import { useAuthStore } from '@/lib/stores/auth-store'
import { SimpleChat } from '@/components/simple/SimpleChat'
import { Sparkles } from 'lucide-react'

export default function ChatPage() {
  const router = useRouter()
  const chat = useSimpleChat()
  const { setActiveConversation } = useConversationStore()
  const { isAuthenticated } = useAuthStore()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (mounted && !isAuthenticated) {
      router.push('/')
      return
    }

    if (mounted && isAuthenticated) {
      // Clear active conversation on new chat
      setActiveConversation(null)
    }
  }, [mounted, isAuthenticated, setActiveConversation, router])

  if (!mounted || !isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-zinc-950 text-white">
        <div className="text-center">
          <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4 mx-auto animate-pulse">
            <Sparkles className="w-6 h-6 text-primary" />
          </div>
          <h2 className="text-xl font-bold mb-1">K.I.R.A</h2>
          <p className="text-xs text-zinc-500">Đang khởi tạo...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col overflow-hidden bg-background min-h-0">
      {/* Chat Section */}
      <SimpleChat
        messages={chat.messages}
        isLoading={chat.isLoading}
        onSendMessage={chat.sendMessage}
        onClearChat={chat.clearMessages}
        error={chat.error}
      />
    </div>
  )
}
