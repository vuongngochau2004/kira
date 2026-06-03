'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useCallback } from 'react'

/**
 * usePostLoginRedirect - Handle post-login redirect pattern
 *
 * Manages returnUrl storage and redirect logic after authentication.
 * Prevents duplicate code across LoginForm, RegisterForm, and auth pages.
 *
 * Usage:
 *   const { handleRedirect, storeReturnUrl } = usePostLoginRedirect()
 *
 *   // After successful login/register
 *   handleRedirect()
 *
 *   // Store current URL before redirecting to login
 *   storeReturnUrl()
 */
export function usePostLoginRedirect() {
  const router = useRouter()

  /**
   * Execute redirect after successful authentication
   * Checks sessionStorage for returnUrl and redirects accordingly
   */
  const handleRedirect = useCallback(() => {
    const returnUrl = sessionStorage.getItem('returnUrl')
    if (returnUrl) {
      sessionStorage.removeItem('returnUrl')
      router.push(returnUrl)
    } else {
      router.push('/chat')
    }
  }, [router])

  /**
   * Store current URL for post-login redirect
   * Call this before redirecting unauthenticated user to login
   */
  const storeReturnUrl = useCallback((path?: string) => {
    const currentPath = path || window.location.pathname
    sessionStorage.setItem('returnUrl', currentPath)
  }, [])

  return {
    handleRedirect,
    storeReturnUrl,
  }
}

/**
 * Hook for auto-redirect when already authenticated
 * Used in page.tsx to redirect authenticated users away from login page
 *
 * FIXED: Only redirect after auth verification is complete (isVerified)
 * This prevents redirecting when localStorage says authenticated but cookies are invalid
 */
export function useAutoRedirect(isAuthenticated: boolean, isHydrated: boolean, isVerified: boolean) {
  const { handleRedirect } = usePostLoginRedirect()

  useEffect(() => {
    // Only redirect if all three conditions are met:
    // 1. isAuthenticated: localStorage says user is logged in
    // 2. isHydrated: persist middleware has finished hydration
    // 3. isVerified: backend verification has completed
    if (isAuthenticated && isHydrated && isVerified) {
      handleRedirect()
    }
  }, [isAuthenticated, isHydrated, isVerified, handleRedirect])
}
