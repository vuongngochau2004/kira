'use client'

import { useRouter, usePathname } from 'next/navigation'
import { MessageSquare, Search, Upload, Menu } from 'lucide-react'
import { cn } from '@/lib/utils'

interface MobileNavProps {
  onMenuClick?: () => void
}

export function MobileNav({ onMenuClick }: MobileNavProps) {
  const router = useRouter()
  const pathname = usePathname()

  const navItems = [
    { icon: MessageSquare, label: 'Chat', path: '/chat' },
    { icon: Search, label: 'Tìm kiếm', path: '/conversations' },
    { icon: Upload, label: 'Tải lên', path: '/uploads' },
  ]

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-background border-t z-50">
      <div className="flex items-center justify-around h-16">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = pathname === item.path

          return (
            <button
              key={item.path}
              onClick={() => router.push(item.path)}
              className={cn(
                'flex flex-col items-center justify-center gap-1 flex-1 h-full transition-colors',
                isActive ? 'text-primary' : 'text-muted-foreground'
              )}
            >
              <Icon className="w-5 h-5" />
              <span className="text-xs">{item.label}</span>
            </button>
          )
        })}

        {/* Menu Button */}
        <button
          onClick={onMenuClick}
          className="flex flex-col items-center justify-center gap-1 flex-1 h-full text-muted-foreground transition-colors"
        >
          <Menu className="w-5 h-5" />
          <span className="text-xs">Menu</span>
        </button>
      </div>
    </nav>
  )
}
