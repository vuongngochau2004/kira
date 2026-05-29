'use client'

import React from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { useSidebarCollapse } from './useSidebarCollapse'
import { SidebarCollapsed } from './SidebarCollapsed'
import { SidebarExpanded, SidebarPage } from './SidebarExpanded'
import { cn } from '@/lib/utils'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { conversationsAPI } from '@/lib/api/simple-client'
import { useConversationStore } from '@/lib/stores/conversation-store'

interface CollapsibleSidebarProps {
  customContent?: React.ReactNode
}

function getPageFromPath(pathname: string): SidebarPage {
  if (pathname === '/conversations') return 'conversations'
  if (pathname === '/uploads') return 'uploads'
  return 'chat'
}

export function CollapsibleSidebar({ customContent }: CollapsibleSidebarProps) {
  const { isCollapsed, toggle } = useSidebarCollapse()
  const pathname = usePathname()
  const router = useRouter()
  const [currentPage, setCurrentPage] = React.useState<SidebarPage>(() => getPageFromPath(pathname))
  const { setActiveConversation } = useConversationStore()
  const queryClient = useQueryClient()

  // Update page when pathname changes
  React.useEffect(() => {
    setCurrentPage(getPageFromPath(pathname))
  }, [pathname])

  const handlePageChange = (newPage: SidebarPage) => {
    setCurrentPage(newPage)
  }

  // Create conversation mutation
  const createMutation = useMutation({
    mutationFn: () => conversationsAPI.create(),
    onSuccess: (conversation) => {
      setActiveConversation(conversation.id)
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      router.push('/chat')
    },
  })

  const handleCreateConversation = () => {
    createMutation.mutate()
  }

  // On mobile (< 768px), sidebar is always hidden
  // On tablet (768-1024px), defaults to collapsed (72px)
  // On desktop (> 1024px), defaults to expanded (280px)
  return (
    <aside
      className={cn(
        'hidden md:flex md:flex-col border-r bg-background shrink-0 transition-all duration-300 ease-in-out',
        isCollapsed ? 'w-[72px]' : 'w-[280px]'
      )}
    >
      {isCollapsed ? (
        <SidebarCollapsed onToggle={toggle} onCreateConversation={handleCreateConversation} />
      ) : (
        <SidebarExpanded
          page={currentPage}
          onPageChange={handlePageChange}
          onToggle={toggle}
          onCreateConversation={handleCreateConversation}
          customContent={customContent}
        />
      )}
    </aside>
  )
}
