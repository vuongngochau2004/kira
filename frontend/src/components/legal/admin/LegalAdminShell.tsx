'use client'

import type { ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft, Shield } from 'lucide-react'
import { AuthGuard } from '@/components/auth/auth-guard'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/lib/stores/auth-store'

interface LegalAdminShellProps {
  title: string
  description: string
  backHref: string
  actions?: ReactNode
  children: ReactNode
}

export function LegalAdminShell({ title, description, backHref, actions, children }: LegalAdminShellProps) {
  const router = useRouter()
  const { user } = useAuthStore()

  return (
    <AuthGuard>
      <div className="min-h-screen bg-background">
        <header className="sticky top-0 z-20 border-b bg-background/95 backdrop-blur">
          <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-2 px-4">
            <div className="flex min-w-0 items-center gap-2">
              <Button variant="ghost" size="icon" onClick={() => router.push(backHref)} aria-label="Quay lại">
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <div className="min-w-0">
                <h1 className="truncate text-base font-semibold">{title}</h1>
                <p className="truncate text-xs text-muted-foreground">{description}</p>
              </div>
            </div>
            {user?.role === 'admin' && actions}
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6">
          {user?.role !== 'admin' ? (
            <div className="flex min-h-[60vh] flex-col items-center justify-center gap-2 text-center">
              <Shield className="h-8 w-8 text-muted-foreground" />
              <h2 className="text-lg font-semibold">Bạn cần quyền Admin</h2>
            </div>
          ) : (
            children
          )}
        </main>
      </div>
    </AuthGuard>
  )
}
