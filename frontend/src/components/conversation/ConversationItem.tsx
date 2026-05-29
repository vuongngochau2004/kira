'use client'

import { formatDistanceToNow } from 'date-fns'
import { MessageSquare } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Conversation } from '@/lib/api/simple-client'

interface ConversationItemProps {
  conversation: Conversation
  isActive: boolean
  onClick: () => void
  onDelete: () => void
}

export function ConversationItem({
  conversation,
  isActive,
  onClick,
  onDelete,
}: ConversationItemProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left px-3 py-2.5 rounded-xl transition-all group',
        'hover:bg-muted/50',
        isActive && 'bg-muted'
      )}
    >
      <div className="flex items-start gap-3">
        <div className={cn(
          'w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5',
          isActive ? 'bg-primary/10' : 'bg-muted'
        )}>
          <MessageSquare className={cn(
            'w-4 h-4',
            isActive ? 'text-primary' : 'text-muted-foreground'
          )} />
        </div>
        <div className="flex-1 min-w-0">
          <p className={cn(
            'text-sm font-medium truncate',
            isActive ? 'text-foreground' : 'text-muted-foreground'
          )}>
            {conversation.title || 'Cuộc trò chuyện mới'}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {(() => {
              try {
                if (!conversation.updated_at) return ''
                const dateStr = conversation.updated_at.endsWith('Z')
                  ? conversation.updated_at
                  : conversation.updated_at + 'Z'
                const parsed = new Date(dateStr)
                if (isNaN(parsed.getTime())) return ''
                return formatDistanceToNow(parsed, { addSuffix: true })
              } catch (e) {
                return ''
              }
            })()}
          </p>
        </div>
      </div>
    </button>
  )
}
