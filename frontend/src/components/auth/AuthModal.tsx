'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth-store'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
}

export function AuthModal({ isOpen, onClose }: AuthModalProps) {
  const router = useRouter()
  const { isAuthenticated } = useAuthStore()

  const handleLogin = () => {
    onClose()
    router.push('/login')
  }

  const handleRegister = () => {
    onClose()
    router.push('/register')
  }

  // Redirect to chat if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      onClose()
      router.push('/chat')
    }
  }, [isAuthenticated, onClose, router])

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader className="text-center">
          <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mx-auto mb-3">
            <Sparkles className="w-6 h-6 text-primary" />
          </div>
          <DialogTitle className="text-xl">Chào mừng đến với K.I.R.A</DialogTitle>
          <p className="text-sm text-muted-foreground mt-2">
            Đăng nhập hoặc đăng ký để bắt đầu sử dụng trợ lý AI
          </p>
        </DialogHeader>

        <div className="space-y-3 mt-4">
          <Button
            onClick={handleLogin}
            variant="default"
            className="w-full h-11 rounded-xl"
          >
            Đăng nhập
          </Button>
          <Button
            onClick={handleRegister}
            variant="outline"
            className="w-full h-11 rounded-xl"
          >
            Đăng ký tài khoản mới
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
