'use client'

import { useAuthStore } from '@/lib/stores/auth-store'
import { AuthModal } from './AuthModal'
import { useEffect, useState } from 'react'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated } = useAuthStore()
  const [showAuth, setShowAuth] = useState(false)

  useEffect(() => {
    if (!isAuthenticated) {
      setShowAuth(true)
    }
  }, [isAuthenticated])

  if (!isAuthenticated) {
    return (
      <>
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <h2 className="text-2xl font-semibold mb-2">Authentication Required</h2>
            <p className="text-muted-foreground">Please sign in to continue</p>
          </div>
        </div>
        <AuthModal isOpen={showAuth} onClose={() => setShowAuth(false)} />
      </>
    )
  }

  return <>{children}</>
}
