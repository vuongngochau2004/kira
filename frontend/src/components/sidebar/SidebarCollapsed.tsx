'use client'

import { useRouter } from 'next/navigation'
import { Search, Upload, MessageSquarePlus, ChevronRight, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

interface SidebarCollapsedProps {
  onToggle: () => void
  onCreateConversation?: () => void
}

export function SidebarCollapsed({ onToggle, onCreateConversation }: SidebarCollapsedProps) {
  const router = useRouter()

  return (
    <div className="flex flex-col h-full w-[72px] bg-background border-r">
      <TooltipProvider delayDuration={0}>
        {/* Header with Logo and Toggle */}
        <div className="border-b shrink-0">
          {/* Logo */}
          <div className="h-14 flex items-center justify-center">
            <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-primary" />
            </div>
          </div>

          {/* Toggle Button */}
          <div className="flex justify-center pb-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={onToggle}
                  aria-label="Mở rộng thanh bên"
                  aria-expanded="false"
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">
                <p>Mở rộng</p>
              </TooltipContent>
            </Tooltip>
          </div>
        </div>

        {/* Navigation Icons */}
        <div className="flex-1 flex flex-col items-center py-4 gap-2">
          {/* New Conversation */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-10 w-10"
                onClick={onCreateConversation}
                aria-label="Cuộc trò chuyện mới"
              >
                <MessageSquarePlus className="w-5 h-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">
              <p>Cuộc trò chuyện mới</p>
            </TooltipContent>
          </Tooltip>

          {/* Search / Conversations */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-10 w-10"
                onClick={() => router.push('/conversations')}
                aria-label="Tìm kiếm cuộc trò chuyện"
              >
                <Search className="w-5 h-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">
              <p>Tìm kiếm cuộc trò chuyện</p>
            </TooltipContent>
          </Tooltip>

          {/* Upload */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-10 w-10"
                onClick={() => router.push('/uploads')}
                aria-label="Tải lên tài liệu"
              >
                <Upload className="w-5 h-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">
              <p>Tải lên tài liệu</p>
            </TooltipContent>
          </Tooltip>
        </div>
      </TooltipProvider>
    </div>
  )
}
