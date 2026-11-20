'use client'

import { KiraLogoIcon } from '@/components/common/KiraLogo'

interface LoadingScreenProps {
  /**
   * Optional custom label for accessibility
   * @default "Đang tải"
   */
  label?: string
}

/**
 * LoadingScreen - Branded loading state with fade-in animation
 *
 * Features:
 * - Accessibility-first with ARIA attributes
 * - Smooth fade-in transition to prevent flash
 * - Consistent with app background theme
 * - Minimal CSS animation for performance
 *
 * Usage:
 *   <LoadingScreen />
 *   <LoadingScreen label="Đang tải tài liệu..." />
 */
export function LoadingScreen({ label = 'Đang tải' }: LoadingScreenProps) {
  return (
    <div
      className="flex items-center justify-center h-screen bg-background animate-in fade-in duration-300"
      role="status"
      aria-busy="true"
      aria-label={label}
    >
      <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center animate-pulse">
        <KiraLogoIcon size={24} variant="default" />
      </div>
    </div>
  )
}
