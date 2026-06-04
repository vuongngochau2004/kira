'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { AuthGuard } from '@/components/auth/auth-guard'

export default function ChatPage() {
  const router = useRouter()

  useEffect(() => {
    // Immediate redirect to new conversation page
    router.replace('/conversation')
  }, [router])

  return (
    <AuthGuard>
      <div className="h-full flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    </AuthGuard>
  )
}
