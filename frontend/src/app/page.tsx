'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth-store'
import { useAutoRedirect, usePostLoginRedirect } from '@/lib/hooks/use-post-login-redirect'
import { Mail, Lock, User, Eye, EyeOff, Loader2, Github, Chrome, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { KiraLogoIcon } from '@/components/common/KiraLogo'
import { ThemeToggleCompact } from '@/components/common/ThemeToggle'

export default function AuthLandingPage() {
  const router = useRouter()
  const { isAuthenticated, isHydrated, isVerified, login, register, isLoading, error, clearError } = useAuthStore()
  const { handleRedirect } = usePostLoginRedirect()

  // Auto-redirect if already authenticated AND verified
  useAutoRedirect(isAuthenticated, isHydrated, isVerified)

  // State
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()

    if (!email.trim() || !password.trim()) return

    if (mode === 'register' && password.length < 6) {
      alert('Mật khẩu phải có ít nhất 6 ký tự')
      return
    }

    try {
      if (mode === 'login') {
        await login(email.trim(), password)
      } else {
        await register(email.trim(), password, fullName.trim() || undefined)
      }

      handleRedirect()
    } catch (err) {
      // Managed in auth store
    }
  }

  // Toggle between login and registration mode
  const handleToggleMode = () => {
    clearError()
    setMode(prev => prev === 'login' ? 'register' : 'login')
  }

  const handleGoogleLogin = () => {
    window.location.href = `${window.location.origin}/api/v1/auth/google`
  }

  const handleGithubLogin = () => {
    window.location.href = `${window.location.origin}/api/v1/auth/github`
  }

  return (
    <main className="min-h-screen flex flex-col md:flex-row bg-background text-foreground font-sans selection:bg-primary/30 overflow-x-hidden relative transition-colors duration-300">
      {/* Theme Toggle Button */}
      <div className="absolute top-4 right-4 z-20">
        <ThemeToggleCompact />
      </div>
      {/* LEFT COLUMN: Premium Auth Card */}
      <section className="w-full md:w-[45%] flex items-center justify-center p-6 sm:p-10 relative overflow-hidden min-h-[600px] md:min-h-screen">
        {/* Glow ambient spots */}
        <div className="absolute top-1/4 left-1/4 w-72 h-72 bg-primary/10 rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute bottom-1/4 right-1/4 w-72 h-72 bg-violet-600/10 rounded-full blur-[100px] pointer-events-none" />

        {/* Card Container */}
        <div className="w-full max-w-md bg-card/40 backdrop-blur-xl border border-border/80 rounded-3xl p-6 sm:p-8 shadow-2xl relative z-10 hover:border-border transition-all duration-300">
          
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground mb-2 select-none">
              {mode === 'login' ? 'Đăng nhập K.I.R.A' : 'Tạo tài khoản mới'}
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground select-none">
              {mode === 'login' 
                ? 'Nhập tài khoản của bạn để tiếp tục' 
                : 'Đăng ký để khám phá công nghệ phân tích thông minh'}
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs sm:text-sm px-4 py-3 rounded-xl select-none">
                {error}
              </div>
            )}

            {/* Full Name (Registration only) */}
            {mode === 'register' && (
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block">Họ và tên</label>
                <div className="relative rounded-xl border border-border bg-muted/20 focus-within:border-ring transition-all focus-within:ring-2 focus-within:ring-primary/10">
                  <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Nguyễn Văn A"
                    className="w-full pl-10 pr-4 py-3 bg-transparent text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none"
                    required
                  />
                </div>
              </div>
            )}

            {/* Email */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block">Email</label>
              <div className="relative rounded-xl border border-border bg-muted/20 focus-within:border-ring transition-all focus-within:ring-2 focus-within:ring-primary/10">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  className="w-full pl-10 pr-4 py-3 bg-transparent text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none"
                  required
                />
              </div>
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block">Mật khẩu</label>
                {mode === 'login' && (
                  <button
                    type="button"
                    className="text-[10px] font-semibold text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                  >
                    Quên mật khẩu?
                  </button>
                )}
              </div>
              <div className="relative rounded-xl border border-border bg-muted/20 focus-within:border-ring transition-all focus-within:ring-2 focus-within:ring-primary/10">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-10 pr-10 py-3 bg-transparent text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-1 cursor-pointer"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Remember Me checkbox (Login only) */}
            {mode === 'login' && (
              <div className="flex items-center gap-2.5 py-1">
                <input
                  type="checkbox"
                  id="rememberMe"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="w-4 h-4 rounded border-border bg-muted/30 text-primary focus:ring-primary/30 focus:ring-offset-background cursor-pointer"
                />
                <label htmlFor="rememberMe" className="text-xs font-semibold text-muted-foreground select-none cursor-pointer">
                  Duy trì đăng nhập
                </label>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 px-4 rounded-xl bg-primary text-primary-foreground font-bold text-sm hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/10 focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all flex items-center justify-center gap-2 disabled:opacity-50 mt-4 active:scale-[0.98] cursor-pointer"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Đang xử lý...</span>
                </>
              ) : (
                <span>Tiếp tục</span>
              )}
            </button>
          </form>

          {/* Social Divider */}
          <div className="relative my-6 select-none">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">
              <span className="bg-card px-3">Hoặc</span>
            </div>
          </div>

          {/* Social Logins */}
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={handleGoogleLogin}
              className="flex items-center justify-center gap-2 py-3 border border-border bg-muted/10 hover:bg-muted/30 rounded-xl text-xs font-semibold text-muted-foreground hover:text-foreground transition-all active:scale-[0.98] cursor-pointer"
            >
              <Chrome className="w-4 h-4" />
              <span>Google</span>
            </button>

            <button
              type="button"
              onClick={handleGithubLogin}
              className="flex items-center justify-center gap-2 py-3 border border-border bg-muted/10 hover:bg-muted/30 rounded-xl text-xs font-semibold text-muted-foreground hover:text-foreground transition-all active:scale-[0.98] cursor-pointer"
            >
              <Github className="w-4 h-4" />
              <span>GitHub</span>
            </button>
          </div>

          {/* Toggle Switch */}
          <p className="text-center text-xs text-muted-foreground mt-6 select-none">
            {mode === 'login' ? 'Chưa có tài khoản?' : 'Đã có tài khoản?'}
            <button
              type="button"
              onClick={handleToggleMode}
              className="text-foreground font-bold hover:text-primary transition-colors hover:underline ml-1.5 focus:outline-none cursor-pointer"
            >
              {mode === 'login' ? 'Đăng ký ngay' : 'Đăng nhập'}
            </button>
          </p>

        </div>
      </section>

      {/* RIGHT COLUMN: Stunning Dark Brand Panel */}
      <section className="w-full md:w-[55%] flex flex-col justify-between p-10 md:p-20 bg-muted/10 border-t md:border-t-0 md:border-l border-border/80 relative overflow-hidden select-none min-h-[450px] md:min-h-screen">
        
        {/* Glow ambient background elements */}
        <div className="absolute top-1/3 right-1/4 w-[500px] h-[500px] bg-primary/5 rounded-full blur-[140px] pointer-events-none animate-pulse duration-5000" />
        <div className="absolute bottom-1/3 left-1/4 w-[400px] h-[400px] bg-indigo-500/5 rounded-full blur-[140px] pointer-events-none" />
        
        {/* Grid pattern */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808007_1px,transparent_1px),linear-gradient(to_bottom,#80808007_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none" />

        {/* Top Space for logo / branding */}
        <div className="relative z-10 flex items-center gap-3">
          <KiraLogoIcon size={32} variant="default" className="text-primary" />
          <span className="text-sm font-bold tracking-widest text-muted-foreground uppercase">K.I.R.A SYSTEM</span>
        </div>

        {/* Center content: Branding & Core Features */}
        <div className="relative z-10 my-auto py-12">
          {/* Main Title resembling LeadZen styling with clean underline */}
          <div className="mb-6">
            <h2 className="text-5xl md:text-7xl font-extrabold tracking-tight bg-gradient-to-r from-foreground via-foreground/90 to-foreground/75 bg-clip-text text-transparent mb-1 flex items-baseline select-none">
              K.I.R.A
            </h2>
            <div className="w-16 h-1 bg-primary rounded-full mb-6 mt-1" />
            <p className="text-lg md:text-xl font-semibold text-foreground max-w-lg leading-relaxed">
              Knowledge & Intelligent Robotic Assistant
            </p>
            <p className="text-sm text-muted-foreground max-w-md mt-1 leading-relaxed">
              Trợ lý AI thế hệ mới giúp phân tích tài liệu học thuật bằng công nghệ RAG và Knowledge Graph.
            </p>
          </div>

          {/* Features Steps resembling screenshot's 1, 2, 3 list */}
          <div className="space-y-6 mt-10 max-w-xl">
            {/* Step 1 */}
            <div className="flex items-start gap-4 group">
              <div className="w-8 h-8 rounded-full border border-border bg-card flex items-center justify-center text-xs font-bold text-muted-foreground group-hover:border-primary/50 group-hover:text-primary transition-all shrink-0 shadow-lg shadow-black/5 dark:shadow-black/30">
                1
              </div>
              <div>
                <h3 className="text-sm font-semibold text-foreground/90 group-hover:text-foreground transition-colors">
                  Phân tích tài liệu thông minh
                </h3>
                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                  Tải lên tài liệu PDF, DOCX, TXT. K.I.R.A tự động trích xuất kiến thức và mô hình hóa dưới dạng biểu đồ tri thức.
                </p>
              </div>
            </div>

            {/* Step 2 */}
            <div className="flex items-start gap-4 group">
              <div className="w-8 h-8 rounded-full border border-border bg-card flex items-center justify-center text-xs font-bold text-muted-foreground group-hover:border-primary/50 group-hover:text-primary transition-all shrink-0 shadow-lg shadow-black/5 dark:shadow-black/30">
                2
              </div>
              <div>
                <h3 className="text-sm font-semibold text-foreground/90 group-hover:text-foreground transition-colors">
                  Tra cứu RAG chuẩn xác
                </h3>
                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                  Đặt câu hỏi học thuật và nhận câu trả lời được tổng hợp tự động từ tài liệu gốc, kèm trích dẫn nguồn chi tiết.
                </p>
              </div>
            </div>

            {/* Step 3 */}
            <div className="flex items-start gap-4 group">
              <div className="w-8 h-8 rounded-full border border-border bg-card flex items-center justify-center text-xs font-bold text-muted-foreground group-hover:border-primary/50 group-hover:text-primary transition-all shrink-0 shadow-lg shadow-black/5 dark:shadow-black/30">
                3
              </div>
              <div>
                <h3 className="text-sm font-semibold text-foreground/90 group-hover:text-foreground transition-colors">
                  Tương tác AI thời gian thực
                </h3>
                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                  Trải nghiệm tốc độ phản hồi cực nhanh thông qua luồng stream token-by-token và các bước suy nghĩ collapsible.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="relative z-10 flex items-center justify-between text-[10px] text-muted-foreground/60 tracking-wider">
          <span>© 2026 K.I.R.A. All rights reserved.</span>
          <span>BUILD 1.2.0</span>
        </div>

      </section>
    </main>
  )
}
