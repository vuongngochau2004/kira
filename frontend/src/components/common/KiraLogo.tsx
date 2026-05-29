'use client'

import { cn } from '@/lib/utils'

/**
 * K.I.R.A Logo System
 * Knowledge. Intelligence. Research. Assistant.
 *
 * Logo variants for different contexts and sizes.
 * All logos use SVG for perfect scalability at any size.
 */

// ============================================================================
// BASE LOGO COMPONENTS
// ============================================================================

interface LogoIconProps {
  size?: number
  className?: string
  variant?: 'default' | 'gradient' | 'minimal' | 'outline' | 'filled'
}

/**
 * Kira Logo Icon - Abstract hexagonal AI brain symbol
 * Represents: Knowledge (hexagon), Intelligence (neural connections), Research (precision)
 */
export function KiraLogoIcon({ size = 64, className, variant = 'default' }: LogoIconProps) {
  const baseProps = {
    width: size,
    height: size,
    viewBox: '0 0 64 64',
    fill: 'none',
    xmlns: 'http://www.w3.org/2000/svg',
    className,
  }

  switch (variant) {
    case 'gradient':
      return (
        <svg {...baseProps}>
          <defs>
            <linearGradient id="kiraGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#6366F1" />
              <stop offset="50%" stopColor="#8B5CF6" />
              <stop offset="100%" stopColor="#EC4899" />
            </linearGradient>
          </defs>
          {/* Hexagon Frame */}
          <path
            d="M32 4L56 18V46L32 60L8 46V18L32 4Z"
            stroke="url(#kiraGradient)"
            strokeWidth="2"
            fill="none"
          />
          {/* Inner Neural Pattern */}
          <circle cx="32" cy="32" r="8" fill="url(#kiraGradient)" opacity="0.8" />
          <circle cx="32" cy="32" r="14" stroke="url(#kiraGradient)" strokeWidth="1.5" opacity="0.6" />
          {/* Neural Nodes */}
          <circle cx="32" cy="18" r="3" fill="url(#kiraGradient)" />
          <circle cx="44" cy="26" r="3" fill="url(#kiraGradient)" />
          <circle cx="44" cy="38" r="3" fill="url(#kiraGradient)" />
          <circle cx="32" cy="46" r="3" fill="url(#kiraGradient)" />
          <circle cx="20" cy="38" r="3" fill="url(#kiraGradient)" />
          <circle cx="20" cy="26" r="3" fill="url(#kiraGradient)" />
          {/* Neural Connections */}
          <line x1="32" y1="21" x2="32" y2="24" stroke="url(#kiraGradient)" strokeWidth="1.5" />
          <line x1="41" y1="26" x2="38" y2="28" stroke="url(#kiraGradient)" strokeWidth="1.5" />
          <line x1="41" y1="38" x2="38" y2="36" stroke="url(#kiraGradient)" strokeWidth="1.5" />
          <line x1="32" y1="43" x2="32" y2="40" stroke="url(#kiraGradient)" strokeWidth="1.5" />
          <line x1="23" y1="38" x2="26" y2="36" stroke="url(#kiraGradient)" strokeWidth="1.5" />
          <line x1="23" y1="26" x2="26" y2="28" stroke="url(#kiraGradient)" strokeWidth="1.5" />
        </svg>
      )

    case 'minimal':
      return (
        <svg {...baseProps}>
          {/* Minimal K Lettermark */}
          <path
            d="M24 16V48M24 16L40 16M24 32L40 32"
            stroke="currentColor"
            strokeWidth="4"
            strokeLinecap="round"
          />
        </svg>
      )

    case 'outline':
      return (
        <svg {...baseProps}>
          {/* Hexagon Outline */}
          <path
            d="M32 4L56 18V46L32 60L8 46V18L32 4Z"
            stroke="currentColor"
            strokeWidth="2"
            fill="none"
          />
          {/* K Letter */}
          <text
            x="32"
            y="42"
            textAnchor="middle"
            fontSize="24"
            fontWeight="bold"
            fill="currentColor"
            fontFamily="system-ui, sans-serif"
          >
            K
          </text>
        </svg>
      )

    case 'filled':
      return (
        <svg {...baseProps}>
          <defs>
            <linearGradient id="kiraFilledGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#6366F1" />
              <stop offset="100%" stopColor="#8B5CF6" />
            </linearGradient>
          </defs>
          {/* Filled Hexagon */}
          <path
            d="M32 4L56 18V46L32 60L8 46V18L32 4Z"
            fill="url(#kiraFilledGradient)"
          />
          {/* White K */}
          <text
            x="32"
            y="42"
            textAnchor="middle"
            fontSize="24"
            fontWeight="bold"
            fill="white"
            fontFamily="system-ui, sans-serif"
          >
            K
          </text>
        </svg>
      )

    default: // default variant
      return (
        <svg {...baseProps}>
          {/* Hexagon Frame */}
          <path
            d="M32 4L56 18V46L32 60L8 46V18L32 4Z"
            stroke="currentColor"
            strokeWidth="2"
            fill="none"
          />
          {/* Inner Neural Pattern */}
          <circle cx="32" cy="32" r="8" fill="currentColor" opacity="0.3" />
          <circle cx="32" cy="32" r="14" stroke="currentColor" strokeWidth="1.5" opacity="0.5" />
          {/* Neural Nodes */}
          <circle cx="32" cy="18" r="2.5" fill="currentColor" />
          <circle cx="44" cy="26" r="2.5" fill="currentColor" />
          <circle cx="44" cy="38" r="2.5" fill="currentColor" />
          <circle cx="32" cy="46" r="2.5" fill="currentColor" />
          <circle cx="20" cy="38" r="2.5" fill="currentColor" />
          <circle cx="20" cy="26" r="2.5" fill="currentColor" />
          {/* Neural Connections */}
          <line x1="32" y1="20.5" x2="32" y2="24" stroke="currentColor" strokeWidth="1.5" opacity="0.6" />
          <line x1="41.5" y1="26" x2="38" y2="28" stroke="currentColor" strokeWidth="1.5" opacity="0.6" />
          <line x1="41.5" y1="38" x2="38" y2="36" stroke="currentColor" strokeWidth="1.5" opacity="0.6" />
          <line x1="32" y1="43.5" x2="32" y2="40" stroke="currentColor" strokeWidth="1.5" opacity="0.6" />
          <line x1="22.5" y1="38" x2="26" y2="36" stroke="currentColor" strokeWidth="1.5" opacity="0.6" />
          <line x1="22.5" y1="26" x2="26" y2="28" stroke="currentColor" strokeWidth="1.5" opacity="0.6" />
        </svg>
      )
  }
}

// ============================================================================
// FULL LOGO WITH TEXT
// ============================================================================

interface KiraLogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
  variant?: 'default' | 'gradient' | 'minimal' | 'outline' | 'filled'
  showTagline?: boolean
}

const sizeConfig = {
  sm: { icon: 32, text: 'text-lg' },
  md: { icon: 48, text: 'text-xl' },
  lg: { icon: 64, text: 'text-2xl' },
  xl: { icon: 96, text: 'text-3xl' },
}

/**
 * Full K.I.R.A Logo with name and optional tagline
 */
export function KiraLogo({ size = 'lg', className, variant = 'default', showTagline = true }: KiraLogoProps) {
  const config = sizeConfig[size]

  return (
    <div className={cn('flex flex-col items-center justify-center', className)}>
      {/* Logo Icon */}
      <KiraLogoIcon size={config.icon} variant={variant} className="mb-3" />

      {/* Brand Name */}
      <h1 className={cn('font-bold tracking-wider', config.text)}>
        K.I.R.A
      </h1>

      {/* Tagline */}
      {showTagline && (
        <p className="text-sm text-muted-foreground mt-1 tracking-wide">
          Knowledge • Intelligence • Research • Assistant
        </p>
      )}
    </div>
  )
}

// ============================================================================
// WELCOME STATE COMPONENT
// ============================================================================

interface KiraWelcomeProps {
  className?: string
  variant?: 'default' | 'gradient' | 'minimal' | 'outline' | 'filled'
}

/**
 * Welcome screen with logo, tagline, and helpful hints
 */
export function KiraWelcome({ className, variant = 'gradient' }: KiraWelcomeProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12', className)}>
      {/* Animated Logo */}
      <div className="relative mb-6">
        {/* Pulse Effect */}
        <div className="absolute inset-0 bg-primary/20 rounded-full blur-2xl animate-pulse" />
        <KiraLogoIcon size={96} variant={variant} className="relative" />
      </div>

      {/* Brand Name */}
      <h2 className="text-2xl font-semibold mb-2 tracking-wider">K.I.R.A</h2>

      {/* Tagline */}
      <p className="text-sm text-muted-foreground mb-6 max-w-xs text-center">
        Trợ lý AI nghiên cứu của bạn
      </p>

      {/* Hints */}
      <div className="flex flex-col gap-2 text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-primary/60" />
          <span>Hãy đặt câu hỏi để bắt đầu</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-primary/60" />
          <span>Hoặc tải lên tài liệu để phân tích</span>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// LOADING SPINNER WITH LOGO
// ============================================================================

interface KiraLogoLoaderProps {
  size?: number
  className?: string
}

/**
 * Animated logo loader for loading states
 */
export function KiraLogoLoader({ size = 32, className }: KiraLogoLoaderProps) {
  return (
    <div className={cn('relative', className)} style={{ width: size, height: size }}>
      {/* Spinning Ring */}
      <svg
        className="absolute inset-0 animate-spin"
        width={size}
        height={size}
        viewBox="0 0 64 64"
      >
        <path
          d="M32 4L56 18V46L32 60L8 46V18L32 4Z"
          stroke="currentColor"
          strokeWidth="2"
          fill="none"
          opacity="0.3"
          strokeDasharray="8 8"
        />
      </svg>
      {/* Center Dot */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-2 h-2 rounded-full bg-current animate-pulse" />
      </div>
    </div>
  )
}

// ============================================================================
// EXPORT ALL
// ============================================================================

export default KiraLogo
