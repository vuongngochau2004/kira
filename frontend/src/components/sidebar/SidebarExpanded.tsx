'use client'

import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth-store'
import { Sparkles, LogOut, ChevronLeft, Search, Upload, MessageSquarePlus } from 'lucide-react'
import { Button } from '@/components/ui/button'
export type SidebarPage = 'chat' | 'conversations' | 'uploads'

interface SidebarExpandedProps {
  page: SidebarPage
  onPageChange?: (page: SidebarPage) => void
  onToggle: () => void
  onCreateConversation?: () => void
  customContent?: React.ReactNode
}

export function SidebarExpanded({
  page,
  onPageChange,
  onToggle,
  onCreateConversation,
  customContent,
}: SidebarExpandedProps) {
  const router = useRouter()
  const { user, logout } = useAuthStore()

  return (
    <div className="flex flex-col h-full w-[280px] bg-background border-r">
      {/* Header with Logo and Toggle */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
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
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={onToggle}
            aria-label="Thu gọn thanh bên"
            aria-expanded="true"
          >
            <ChevronLeft className="w-4 h-4" />
          </Button>
        </div>

        {/* Navigation Buttons - Vertical Stack */}
        <div className="space-y-2">
          {/* New Chat Button */}
          <Button
            variant={page === 'chat' ? 'default' : 'outline'}
            className="w-full justify-start"
            onClick={() => {
              onCreateConversation?.()
            }}
          >
            <MessageSquarePlus className="w-4 h-4 mr-2" />
            Cuộc trò chuyện mới
          </Button>

          {/* Search Button */}
          <Button
            variant={page === 'conversations' ? 'default' : 'outline'}
            className="w-full justify-start"
            onClick={() => {
              onPageChange?.('conversations')
              router.push('/conversations')
            }}
          >
            <Search className="w-4 h-4 mr-2" />
            Tìm kiếm cuộc trò chuyện
          </Button>

          {/* Documents Button */}
          <Button
            variant={page === 'uploads' ? 'default' : 'outline'}
            className="w-full justify-start"
            onClick={() => {
              onPageChange?.('uploads')
              router.push('/uploads')
            }}
          >
            <Upload className="w-4 h-4 mr-2" />
            Tài liệu
          </Button>
        </div>
      </div>

      {/* Custom Content */}
      {customContent || (
        <div className="flex-1 overflow-y-auto min-h-0">
          <div className="p-4 text-center text-sm text-muted-foreground">
            <p>Chọn một hành động từ menu để bắt đầu.</p>
          </div>
        </div>
      )}

      {/* User Footer */}
      {user && (
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
    </div>
  )
}
