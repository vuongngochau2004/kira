'use client'

import { useState, useEffect } from 'react'
import { Sun, Moon, Monitor } from 'lucide-react'
import { useTheme } from '@/lib/stores/theme-store'
import { cn } from '@/lib/utils'

/**
 * Theme Toggle Component
 *
 * Allows users to switch between light, dark, and system themes.
 * Displays the current effective theme with animated icon transitions.
 */

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, setTheme, effectiveTheme } = useTheme()

  const themes: Array<{ value: 'light' | 'dark' | 'system'; icon: typeof Sun; label: string }> = [
    { value: 'light', icon: Sun, label: 'Sáng' },
    { value: 'dark', icon: Moon, label: 'Tối' },
    { value: 'system', icon: Monitor, label: 'Hệ thống' },
  ]

  return (
    <div className={cn('flex items-center bg-muted rounded-lg p-1', className)}>
      {themes.map(({ value, icon: Icon, label }) => {
        const isActive = theme === value
        // Show dot indicator for the effective theme when in system mode
        const isEffective = value === 'system' && (
          (effectiveTheme === 'dark' && theme === 'system') ||
          (effectiveTheme === 'light' && theme === 'system')
        )

        return (
          <button
            key={value}
            onClick={() => setTheme(value)}
            className={cn(
              'relative flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-all duration-200',
              'hover:bg-background/80',
              isActive
                ? 'bg-background shadow-sm text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            )}
            title={label}
          >
            <Icon className="w-4 h-4" />
            {/* Show effective theme indicator for system mode */}
            {isEffective && (
              <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-primary" />
            )}
          </button>
        )
      })}
    </div>
  )
}

/**
 * Compact Theme Toggle (Icon-only)
 *
 * Minimal version with just a single button that cycles through themes
 */
export function ThemeToggleCompact({ className }: { className?: string }) {
  const { theme, setTheme, effectiveTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  const cycleTheme = () => {
    const themes: Array<'light' | 'dark' | 'system'> = ['light', 'dark', 'system']
    const currentIndex = themes.indexOf(theme as 'light' | 'dark' | 'system')
    const nextIndex = (currentIndex + 1) % themes.length
    setTheme(themes[nextIndex])
  }

  // Show current effective theme icon (default to Moon during SSR)
  const Icon = !mounted ? Moon : (effectiveTheme === 'dark' ? Moon : Sun)

  return (
    <button
      onClick={cycleTheme}
      className={cn(
        'relative flex items-center justify-center w-9 h-9 rounded-lg transition-all duration-200',
        'hover:bg-muted text-muted-foreground hover:text-foreground',
        className
      )}
      title={theme === 'system' ? `Hệ thống (${effectiveTheme === 'dark' ? 'Tối' : 'Sáng'})` : (effectiveTheme === 'dark' ? 'Tối' : 'Sáng')}
    >
      <Icon className="w-4 h-4" />
      {theme === 'system' && (
        <span className="absolute top-1 right-1 w-1 h-1 rounded-full bg-primary" />
      )}
    </button>
  )
}

/**
 * Theme Toggle Dropdown
 *
 * Button that shows a dropdown menu with all theme options
 */
export function ThemeToggleDropdown({ className }: { className?: string }) {
  const { theme, setTheme, effectiveTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  const themes: Array<{ value: 'light' | 'dark' | 'system'; icon: typeof Sun; label: string }> = [
    { value: 'light', icon: Sun, label: 'Sáng' },
    { value: 'dark', icon: Moon, label: 'Tối' },
    { value: 'system', icon: Monitor, label: 'Hệ thống' },
  ]

  // Use Moon as default during SSR to prevent hydration mismatch
  const CurrentIcon = !mounted ? Moon : (effectiveTheme === 'dark' ? Moon : Sun)

  return (
    <div className={cn('relative group', className)}>
      <button
        className={cn(
          'flex items-center justify-center w-9 h-9 rounded-lg transition-all duration-200',
          'hover:bg-muted text-muted-foreground hover:text-foreground'
        )}
        title="Chuyển đổi giao diện"
      >
        <CurrentIcon className="w-4 h-4" />
      </button>

      {/* Dropdown Menu */}
      <div className="absolute bottom-full mb-1 left-0 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
        <div className="bg-popover text-popover-foreground rounded-lg shadow-lg border p-1 min-w-[140px]">
          {themes.map(({ value, icon: Icon, label }) => {
            const isActive = theme === value
            return (
              <button
                key={value}
                onClick={() => setTheme(value)}
                className={cn(
                  'w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors',
                  'hover:bg-muted',
                  isActive ? 'bg-muted text-foreground' : 'text-muted-foreground'
                )}
              >
                <Icon className="w-4 h-4" />
                <span>{label}</span>
                {isActive && (
                  <span className="ml-auto w-1.5 h-1.5 rounded-full bg-primary" />
                )}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
