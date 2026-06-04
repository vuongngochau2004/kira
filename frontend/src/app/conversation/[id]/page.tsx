'use client'

import { useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { AuthGuard } from '@/components/auth/auth-guard'
import { isValidUUID } from '@/lib/utils/uuid'

export default function ConversationIdPage() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string

  useEffect(() => {
    if (!id) {
      router.replace('/conversation')
      return
    }

    // Validate UUID format
    if (!isValidUUID(id)) {
      console.warn(`Invalid conversation ID format: ${id}`)
      router.replace('/conversation')
      return
    }

    // Redirect to new query param format
    router.replace(`/conversation?id=${id}`)
  }, [id, router])

  return (
    <AuthGuard>
      <div className="h-full flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    </AuthGuard>
  )
}
