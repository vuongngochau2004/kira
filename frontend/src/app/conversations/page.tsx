'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useConversationStore } from '@/lib/stores/conversation-store'
import { useAuthStore } from '@/lib/stores/auth-store'
import { conversationsAPI } from '@/lib/api/simple-client'
import { ConversationItem } from '@/components/conversation/ConversationItem'
import { DeleteConfirmDialog } from '@/components/conversation/DeleteConfirmDialog'
import { Sparkles, ArrowLeft, Trash2, CheckSquare, Square } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export default function ConversationsPage() {
  const router = useRouter()
  const { activeConversationId, setActiveConversation } = useConversationStore()
  const { isAuthenticated } = useAuthStore()
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [mounted, setMounted] = useState(false)
  const queryClient = useQueryClient()

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (mounted && !isAuthenticated) {
      router.push('/')
    }
  }, [mounted, isAuthenticated, router])

  const { data, isLoading } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => conversationsAPI.list(1, 100),
    enabled: mounted && isAuthenticated,
  })

  const createMutation = useMutation({
    mutationFn: () => conversationsAPI.create(),
    onSuccess: (conversation) => {
      setActiveConversation(conversation.id)
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      router.push('/chat')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => conversationsAPI.delete(id),
    onSuccess: () => {
      if (activeConversationId === deleteId) {
        setActiveConversation(null)
      }
      setDeleteId(null)
      setSelectedIds(new Set())
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
    },
  })

  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: string[]) => Promise.all(ids.map(id => conversationsAPI.delete(id))),
    onSuccess: () => {
      if (selectedIds.has(activeConversationId || '')) {
        setActiveConversation(null)
      }
      setSelectedIds(new Set())
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
    },
  })

  const handleDelete = () => {
    if (deleteId) {
      deleteMutation.mutate(deleteId)
    }
  }

  const handleBulkDelete = () => {
    if (selectedIds.size > 0) {
      bulkDeleteMutation.mutate(Array.from(selectedIds))
    }
  }

  const toggleSelect = (id: string) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  const toggleSelectAll = () => {
    if (selectedIds.size === filteredConversations.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filteredConversations.map(c => c.id)))
    }
  }

  const filteredConversations = data?.items?.filter(conv => {
    const title = conv.title || 'Cuộc trò chuyện mới'
    return title.toLowerCase().includes(searchQuery.toLowerCase())
  }) || []

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
    <div className="flex flex-col h-screen bg-background">
      {/* Header */}
      <div className="h-14 border-b flex items-center px-4 shrink-0">
        <Button
          variant="ghost"
          size="sm"
          className="gap-2"
          onClick={() => router.push('/chat')}
        >
          <ArrowLeft className="w-4 h-4" />
          Quay lại chat
        </Button>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        <div className="max-w-4xl mx-auto h-full flex flex-col">
          {/* Page Header */}
          <div className="p-6 border-b">
            <h1 className="text-2xl font-bold mb-1">Cuộc trò chuyện</h1>
            <p className="text-sm text-muted-foreground">
              Quản lý tất cả cuộc trò chuyện của bạn
            </p>
          </div>

          {/* Actions Bar */}
          <div className="p-4 border-b flex items-center justify-between gap-4">
            <input
              type="text"
              placeholder="Tìm kiếm cuộc trò chuyện..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="flex-1 max-w-md px-4 py-2 text-sm rounded-lg border border-input bg-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
            />

            <div className="flex items-center gap-2">
              {selectedIds.size > 0 && (
                <>
                  <span className="text-sm text-muted-foreground">
                    {selectedIds.size} được chọn
                  </span>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={handleBulkDelete}
                    disabled={bulkDeleteMutation.isPending}
                  >
                    <Trash2 className="w-4 h-4 mr-1" />
                    Xóa {selectedIds.size}
                  </Button>
                </>
              )}
              <Button onClick={() => createMutation.mutate()}>
                Cuộc trò chuyện mới
              </Button>
            </div>
          </div>

          {/* Conversations List */}
          <div className="flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-2">
                    <Sparkles className="w-4 h-4 text-primary animate-pulse" />
                  </div>
                  <p className="text-sm text-muted-foreground">Đang tải...</p>
                </div>
              </div>
            ) : filteredConversations.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center p-6">
                <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
                  <Sparkles className="w-8 h-8 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-semibold mb-1">
                  {searchQuery ? 'Không tìm thấy cuộc trò chuyện nào' : 'Chưa có cuộc trò chuyện nào'}
                </h3>
                <p className="text-sm text-muted-foreground mb-4">
                  {searchQuery ? 'Thử từ khóa khác' : 'Bắt đầu cuộc trò chuyện đầu tiên của bạn'}
                </p>
                {!searchQuery && (
                  <Button onClick={() => createMutation.mutate()}>
                    Tạo cuộc trò chuyện mới
                  </Button>
                )}
              </div>
            ) : (
              <div className="divide-y">
                {/* Select All Header */}
                <div className="px-6 py-2 bg-muted/30 flex items-center gap-2">
                  <button
                    onClick={toggleSelectAll}
                    className="p-1 hover:bg-muted rounded transition-colors"
                  >
                    {selectedIds.size === filteredConversations.length ? (
                      <CheckSquare className="w-4 h-4 text-primary" />
                    ) : (
                      <Square className="w-4 h-4 text-muted-foreground" />
                    )}
                  </button>
                  <span className="text-sm text-muted-foreground">
                    Chọn tất cả ({filteredConversations.length})
                  </span>
                </div>

                {filteredConversations.map((conversation) => (
                  <div
                    key={conversation.id}
                    className={cn(
                      'flex items-center gap-3 px-6 py-3 hover:bg-muted/50 transition-colors',
                      selectedIds.has(conversation.id) && 'bg-primary/5'
                    )}
                  >
                    <button
                      onClick={() => toggleSelect(conversation.id)}
                      className="p-1 hover:bg-muted rounded transition-colors shrink-0"
                    >
                      {selectedIds.has(conversation.id) ? (
                        <CheckSquare className="w-4 h-4 text-primary" />
                      ) : (
                        <Square className="w-4 h-4 text-muted-foreground" />
                      )}
                    </button>

                    <div
                      className="flex-1 cursor-pointer"
                      onClick={() => {
                        setActiveConversation(conversation.id)
                        router.push(`/conversation/${conversation.id}`)
                      }}
                    >
                      <ConversationItem
                        conversation={conversation}
                        isActive={conversation.id === activeConversationId}
                        onClick={() => {
                          setActiveConversation(conversation.id)
                          router.push(`/conversation/${conversation.id}`)
                        }}
                        onDelete={() => setDeleteId(conversation.id)}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <DeleteConfirmDialog
        isOpen={!!deleteId}
        onClose={() => setDeleteId(null)}
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
      />
    </div>
  )
}
