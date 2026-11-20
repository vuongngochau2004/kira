'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useConversationStore } from '@/features/chat/stores/conversation-store'
import { conversationsAPI } from '@/lib/api/client'
import { ConversationItem } from '@/features/chat/components/ConversationItem'
import { DeleteConfirmDialog } from '@/features/chat/components/DeleteConfirmDialog'
import { Sparkles, ArrowLeft, Trash2, CheckSquare, Square } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { AuthGuard } from '@/features/auth/components/AuthGuard'

export default function ConversationsPage() {
  const router = useRouter()
  const { activeConversationId, setActiveConversation } = useConversationStore()
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [isBulkConfirmOpen, setIsBulkConfirmOpen] = useState(false)
  const queryClient = useQueryClient()

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(searchQuery.trim()), 300)
    return () => window.clearTimeout(timer)
  }, [searchQuery])

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['conversations', page, debouncedSearch],
    queryFn: () => conversationsAPI.list(page, 20, debouncedSearch),
    enabled: true, // AuthGuard ensures auth before render
  })

  const handleNewConversation = () => {
    setActiveConversation(null)
    router.push('/conversation')
  }

  const deleteMutation = useMutation({
    mutationFn: (id: string) => conversationsAPI.delete(id),
    onSuccess: () => {
      if (activeConversationId === deleteId) {
        setActiveConversation(null)
      }
      setDeleteId(null)
      setSelectedIds(new Set())
      void queryClient.invalidateQueries({ queryKey: ['conversations'] })
    },
  })

  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: string[]) => Promise.all(ids.map(id => conversationsAPI.delete(id))),
    onSuccess: () => {
      if (selectedIds.has(activeConversationId || '')) {
        setActiveConversation(null)
      }
      setSelectedIds(new Set())
      setIsBulkConfirmOpen(false)
      void queryClient.invalidateQueries({ queryKey: ['conversations'] })
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

  const changePage = (nextPage: number): void => {
    setSelectedIds(new Set())
    setPage(nextPage)
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

  const filteredConversations = data?.items || []

  return (
    <AuthGuard>
      <div className="flex flex-col h-screen bg-background">
        {/* Header */}
        <div className="h-14 border-b flex items-center px-4 shrink-0">
          <Button
            variant="ghost"
            size="sm"
            className="gap-2"
            onClick={() => router.push('/conversation')}
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
                aria-label="Tìm kiếm cuộc trò chuyện"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value)
                  setSelectedIds(new Set())
                  setPage(1)
                }}
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
                      onClick={() => setIsBulkConfirmOpen(true)}
                      disabled={bulkDeleteMutation.isPending}
                    >
                      <Trash2 className="w-4 h-4 mr-1" />
                      Xóa {selectedIds.size}
                    </Button>
                  </>
                )}
                <Button onClick={handleNewConversation}>
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
              ) : isError ? (
                <div role="alert" className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
                  <p>Không thể tải cuộc trò chuyện. Vui lòng thử lại.</p>
                  <Button variant="outline" onClick={() => void refetch()}>Thử lại</Button>
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
                    <Button onClick={handleNewConversation}>
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
                      aria-label={selectedIds.size === filteredConversations.length ? 'Bỏ chọn tất cả' : 'Chọn tất cả'}
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
                        aria-label={selectedIds.has(conversation.id) ? `Bỏ chọn ${conversation.title || 'cuộc trò chuyện'}` : `Chọn ${conversation.title || 'cuộc trò chuyện'}`}
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
            {data && data.total > data.page_size && (
              <div className="flex items-center justify-center gap-3 border-t p-3 text-sm">
                <Button variant="outline" size="sm" disabled={page === 1} onClick={() => changePage(page - 1)}>Trước</Button>
                <span>Trang {page} / {Math.ceil(data.total / data.page_size)}</span>
                <Button variant="outline" size="sm" disabled={page >= Math.ceil(data.total / data.page_size)} onClick={() => changePage(page + 1)}>Sau</Button>
              </div>
            )}
            {(deleteMutation.isError || bulkDeleteMutation.isError) && (
              <p role="alert" className="p-3 text-center text-sm text-destructive">Không thể xóa cuộc trò chuyện. Vui lòng thử lại.</p>
            )}
          </div>
        </div>

        <DeleteConfirmDialog
          isOpen={!!deleteId}
          onClose={() => setDeleteId(null)}
          onConfirm={handleDelete}
          isLoading={deleteMutation.isPending}
        />
        <DeleteConfirmDialog
          isOpen={isBulkConfirmOpen}
          onClose={() => setIsBulkConfirmOpen(false)}
          onConfirm={handleBulkDelete}
          isLoading={bulkDeleteMutation.isPending}
          count={selectedIds.size}
        />
      </div>
    </AuthGuard>
  )
}
