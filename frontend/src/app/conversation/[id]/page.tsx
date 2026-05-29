'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useConversationStore } from '@/lib/stores/conversation-store'
import { useAuthStore } from '@/lib/stores/auth-store'
import { SimpleChat } from '@/components/simple/SimpleChat'
import { useSimpleChat } from '@/lib/hooks/use-simple-chat'
import { Sparkles } from 'lucide-react'

export default function ConversationPage() {
  const params = useParams()
  const router = useRouter()
  const { isAuthenticated } = useAuthStore()
  const { setActiveConversation, clearActiveConversation } = useConversationStore()
  const chat = useSimpleChat()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (!mounted) return

    if (!isAuthenticated) {
      router.push('/')
      return
    }

    if (params.id) {
      setActiveConversation(params.id as string)
    }

    return () => {
      clearActiveConversation()
    }
  }, [params.id, isAuthenticated, router, setActiveConversation, clearActiveConversation, mounted])

  if (!mounted || !isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-zinc-950 text-white">
        <div className="text-center">
          <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4 mx-auto animate-pulse">
            <Sparkles className="w-6 h-6 text-primary" />
          </div>
          <h2 className="text-xl font-bold mb-1">K.I.R.A</h2>
          <p className="text-xs text-zinc-500">Đang tải cuộc hội thoại...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col overflow-hidden bg-background min-h-0">
      <SimpleChat
        messages={chat.messages}
        isLoading={chat.isLoading}
        onSendMessage={chat.sendMessage}
        onClearChat={chat.clearMessages}
        error={chat.error}
        className="flex-1"
      />
    </div>
  )
}
