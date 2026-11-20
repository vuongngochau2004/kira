'use client'

import { useState, useEffect, useCallback } from 'react'

const STORAGE_KEY = 'sidebar-collapsed'
const BREAKPOINT = 1024 // Desktop breakpoint

interface UseSidebarCollapse {
  isCollapsed: boolean
  toggle: () => void
  setCollapsed: (value: boolean) => void
}

// Safe localStorage operations with error handling
const storage = {
  get: (key: string): string | null => {
    try {
      return localStorage.getItem(key)
    } catch {
      return null
    }
  },
  set: (key: string, value: string): void => {
    try {
      localStorage.setItem(key, value)
    } catch {
      // Silently fail in private browsing
    }
  },
}

export function useSidebarCollapse(): UseSidebarCollapse {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)

    // Check if desktop
    const checkDesktop = () => window.innerWidth >= BREAKPOINT

    // Get stored value or use default based on screen size
    const stored = storage.get(STORAGE_KEY)
    if (stored !== null) {
      setIsCollapsed(stored === 'true')
    } else {
      // Default: collapsed on tablet, expanded on desktop
      setIsCollapsed(!checkDesktop())
    }

    const handleResize = () => {
      // Auto-collapse on tablet, auto-expand on desktop (if not manually set)
      if (storage.get(STORAGE_KEY) === null) {
        setIsCollapsed(!checkDesktop())
      }
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const toggle = useCallback(() => {
    setIsCollapsed(prev => {
      const newValue = !prev
      if (mounted) {
        storage.set(STORAGE_KEY, String(newValue))
      }
      return newValue
    })
  }, [mounted])

  const setCollapsed = useCallback((value: boolean) => {
    setIsCollapsed(value)
    if (mounted) {
      storage.set(STORAGE_KEY, String(value))
    }
  }, [mounted])

  return {
    isCollapsed,
    toggle,
    setCollapsed,
  }
}
