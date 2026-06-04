'use client'

import { useEffect, ReactNode, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth-store'
import { LoadingScreen } from '@/components/common/loading-screen'

interface AuthGuardProps {
  children: ReactNode
  fallback?: ReactNode // Custom loading component
}

/**
 * AuthGuard - Centralized authentication protection with error handling
 *
 * Handles:
 * - Waiting for auth hydration before making decisions
 * - Redirecting unauthenticated users to login
 * - Storing return URL for post-login redirect
 * - Showing loading state during hydration
 * - Error boundary for auth store failures
 *
 * Usage:
 *   <AuthGuard>
 *     <YourProtectedPage />
 *   </AuthGuard>
 */
export function AuthGuard({ children, fallback }: AuthGuardProps) {
  const router = useRouter()
  const pathname = usePathname()
  const [hasError, setHasError] = useState(false)

  // Safely get auth state with error boundary
  let isAuthenticated = false
  let isHydrated = false
  let isVerified = false

  try {
    const authStore = useAuthStore()
    isAuthenticated = authStore.isAuthenticated
    isHydrated = authStore.isHydrated
    isVerified = authStore.isVerified ?? false
  } catch (error) {
    // Auth store failed - treat as unauthenticated for safety
    setHasError(true)
  }

  useEffect(() => {
    // Only redirect after auth state is hydrated AND verified
    // This prevents redirecting during the async hydration delay or verification phase
    if (isHydrated && isVerified && !isAuthenticated && !hasError) {
      // Store current URL for post-login redirect
      try {
        sessionStorage.setItem('returnUrl', pathname)
        router.push('/')
      } catch (error) {
        // Ignore redirect errors
      }
    }
  }, [isHydrated, isVerified, isAuthenticated, pathname, router, hasError])

  // Show error state if auth store failed
  if (hasError) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-red-500">Authentication error. Please refresh the page.</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-primary text-white rounded"
          >
            Refresh
          </button>
        </div>
      </div>
    )
  }

  // Show loading while auth state is hydrating OR being verified with backend
  // This prevents flash of login page before we know the true auth state
  if (!isHydrated || !isVerified) {
    return fallback || <LoadingScreen />
  }

  // If not authenticated after hydration AND verification, return null (will redirect via useEffect)
  if (!isAuthenticated) {
    return null
  }

  // Authenticated and hydrated - render children
  return <>{children}</>
}
