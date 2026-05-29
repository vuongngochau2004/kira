'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth-store'
import { Mail, Lock, User, Sparkles, Github, Chrome } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

export function RegisterForm() {
  const router = useRouter()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const { register, isLoading, error, clearError } = useAuthStore()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()

    if (password.length < 6) {
      alert('Mật khẩu phải có ít nhất 6 ký tự')
      return
    }

    try {
      await register(email, password, fullName || undefined)
      router.push('/chat')
    } catch (err) {
      // Error handled by store
    }
  }

  const handleGoogleLogin = () => {
    // TODO: Implement Google OAuth
    window.location.href = `${window.location.origin}/api/v1/auth/google`
  }

  const handleGithubLogin = () => {
    // TODO: Implement GitHub OAuth
    window.location.href = `${window.location.origin}/api/v1/auth/github`
  }

  return (
    <div className="w-full max-w-md mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
          <Sparkles className="w-6 h-6 text-primary" />
        </div>
        <h1 className="text-2xl font-bold mb-2">Đăng ký</h1>
        <p className="text-sm text-muted-foreground">
          Tạo tài khoản để bắt đầu với K.I.R.A
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-destructive/10 text-destructive text-sm px-4 py-3 rounded-xl">
            {error}
          </div>
        )}

        {/* Full Name */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium">Họ và tên</label>
          <div className="relative">
            <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Nhập họ và tên của bạn"
              className={cn(
                'w-full pl-10 pr-4 py-2.5 rounded-xl border border-input',
                'bg-background placeholder:text-muted-foreground',
                'focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary',
                'transition-all'
              )}
            />
          </div>
        </div>

        {/* Email */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium">Email</label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="nhapemail@example.com"
              className={cn(
                'w-full pl-10 pr-4 py-2.5 rounded-xl border border-input',
                'bg-background placeholder:text-muted-foreground',
                'focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary',
                'transition-all'
              )}
            />
          </div>
        </div>

        {/* Password */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium">Mật khẩu</label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
              className={cn(
                'w-full pl-10 pr-10 py-2.5 rounded-xl border border-input',
                'bg-background placeholder:text-muted-foreground',
                'focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary',
                'transition-all'
              )}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              {showPassword ? (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              )}
            </button>
          </div>
          <p className="text-xs text-muted-foreground">
            Mật khẩu phải có ít nhất 6 ký tự
          </p>
        </div>

        {/* Submit Button */}
        <Button
          type="submit"
          disabled={isLoading}
          className="w-full h-11 rounded-xl text-sm font-medium"
        >
          {isLoading ? 'Đang tạo tài khoản...' : 'Đăng ký bằng email'}
        </Button>
      </form>

      {/* Divider */}
      <div className="relative my-6">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-border" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-background px-2 text-muted-foreground">Hoặc</span>
        </div>
      </div>

      {/* Social Login */}
      <div className="space-y-2">
        <button
          type="button"
          onClick={handleGoogleLogin}
          className={cn(
            'w-full h-11 rounded-xl border border-input flex items-center justify-center gap-3',
            'hover:bg-muted/50 transition-colors'
          )}
        >
          <Chrome className="w-5 h-5" />
          <span className="text-sm font-medium">Đăng ký với Google</span>
        </button>

        <button
          type="button"
          onClick={handleGithubLogin}
          className={cn(
            'w-full h-11 rounded-xl border border-input flex items-center justify-center gap-3',
            'hover:bg-muted/50 transition-colors'
          )}
        >
          <Github className="w-5 h-5" />
          <span className="text-sm font-medium">Đăng ký với GitHub</span>
        </button>
      </div>

      {/* Footer */}
      <p className="text-center text-sm text-muted-foreground mt-6">
        Đã có tài khoản?{' '}
        <button
          type="button"
          onClick={() => router.push('/login')}
          className="text-primary font-medium hover:underline"
        >
          Đăng nhập
        </button>
      </p>
    </div>
  )
}
