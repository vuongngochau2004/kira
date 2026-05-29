'use client'

import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface NewConversationButtonProps {
  onClick: () => void
  isLoading?: boolean
}

export function NewConversationButton({
  onClick,
  isLoading = false,
}: NewConversationButtonProps) {
  return (
    <Button
      onClick={onClick}
      disabled={isLoading}
      className="w-full justify-start"
      variant="outline"
    >
      <Plus className="w-4 h-4 mr-2" />
      New conversation
    </Button>
  )
}
