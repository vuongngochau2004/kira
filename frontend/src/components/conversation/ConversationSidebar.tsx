'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useConversationStore } from '@/lib/stores/conversation-store'
import { conversationsAPI } from '@/lib/api/simple-client'
import { ConversationItem } from './ConversationItem'
import { NewConversationButton } from './NewConversationButton'
import { DeleteConfirmDialog } from './DeleteConfirmDialog'

import { Search, Plus, Sparkles, LogOut } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/lib/stores/auth-store'

interface ConversationSidebarProps {
  className?: string
}

export function ConversationSidebar({ className }: ConversationSidebarProps) {
  const { activeConversationId, setActiveConversation } = useConversationStore()
  const { user, logout, isAuthenticated } = useAuthStore()
  const router = useRouter()
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [mounted, setMounted] = useState(false)

  const queryClient = useQueryClient()

  useEffect(() => {
    setMounted(true)
  }, [])

  // Fetch conversations
  const { data, isLoading } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => conversationsAPI.list(1, 50),
    enabled: mounted && isAuthenticated,
  })

  // Create conversation mutation
  const createMutation = useMutation({
    mutationFn: () => conversationsAPI.create(),
    onSuccess: (conversation) => {
      setActiveConversation(conversation.id)
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
    },
  })

  // Delete conversation mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => conversationsAPI.delete(id),
    onSuccess: () => {
      if (activeConversationId === deleteId) {
        setActiveConversation(null)
      }
      setDeleteId(null)
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
    },
  })

  const handleDelete = () => {
    if (deleteId) {
      deleteMutation.mutate(deleteId)
    }
  }

  // Filter conversations based on search
  const filteredConversations = data?.items?.filter(conv => {
    const title = conv.title || 'Cuộc trò chuyện mới'
    return title.toLowerCase().includes(searchQuery.toLowerCase())
  }) || []

  return (
    <div className={cn('flex flex-col h-full bg-background', className)}>
      {/* Header */}
      <div className="p-4 border-b">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h1 className="text-sm font-bold">K.I.R.A</h1>
            <p className="text-[10px] text-muted-foreground">
              Knowledge & Intelligent Robotic Assistant
            </p>
          </div>
        </div>

        {/* Search Box */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Tìm kiếm cuộc trò chuyện..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={cn(
              'w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-input',
              'bg-background placeholder:text-muted-foreground',
              'focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary',
              'transition-all'
            )}
          />
        </div>

        {/* New Chat Button */}
        <button
          onClick={() => {
            setActiveConversation(null)
            router.push('/chat')
          }}
          className={cn(
            'w-full mt-3 flex items-center justify-center gap-2',
            'px-4 py-2.5 rounded-xl text-sm font-medium',
            'bg-primary text-primary-foreground',
            'hover:bg-primary/90 transition-colors'
          )}
        >
          <Plus className="w-4 h-4" />
          Cuộc trò chuyện mới
        </button>

      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto min-h-0">
        <div className="p-2">
          {isLoading ? (
            <div className="px-3 py-4 text-center text-sm text-muted-foreground">
              Đang tải...
            </div>
          ) : filteredConversations.length === 0 ? (
            <div className="px-3 py-8 text-center">
              {searchQuery ? (
                <p className="text-sm text-muted-foreground">
                  Không tìm thấy cuộc trò chuyện nào
                </p>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Chưa có cuộc trò chuyện nào
                </p>
              )}
            </div>
          ) : (
            <div className="space-y-1">
              {filteredConversations.map((conversation) => (
                <ConversationItem
                   key={conversation.id}
                   conversation={conversation}
                   isActive={conversation.id === activeConversationId}
                   onClick={() => {
                     setActiveConversation(conversation.id)
                     router.push(`/conversation/${conversation.id}`)
                   }}
                   onDelete={() => setDeleteId(conversation.id)}
                />
              ))}

            </div>
          )}
        </div>
      </div>

      {/* User Footer */}
      {mounted && user && (
        <div className="p-4 border-t bg-zinc-900/10 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center font-bold text-xs text-zinc-300 shrink-0">
              {user.full_name ? user.full_name.charAt(0).toUpperCase() : user.email.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-zinc-200 truncate leading-none mb-1">
                {user.full_name || 'Người dùng'}
              </p>
              <p className="text-[10px] text-zinc-500 truncate leading-none">
                {user.email}
              </p>
            </div>
          </div>
          <button
            onClick={() => logout()}
            className="p-1.5 rounded-lg text-zinc-500 hover:text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer shrink-0"
            title="Đăng xuất"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      )}

      <DeleteConfirmDialog
        isOpen={!!deleteId}
        onClose={() => setDeleteId(null)}
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
      />
    </div>
  )
}
