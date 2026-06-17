'use client'

import { useEffect, useMemo, useState, type ElementType } from 'react'
import { useRouter } from 'next/navigation'
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Database,
  Gauge,
  Loader2,
  MessageSquareText,
  RefreshCw,
  Shield,
} from 'lucide-react'
import { AuthGuard } from '@/components/auth/auth-guard'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { adminAPI, AdminOverview, Document } from '@/lib/api/simple-client'
import { useAuthStore } from '@/lib/stores/auth-store'
import { cn } from '@/lib/utils'

function formatDate(value?: string) {
  if (!value) return ''
  return new Intl.DateTimeFormat('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function getStatusTone(status: string) {
  if (status === 'ok' || status === 'completed') return 'border-emerald-700 bg-emerald-700 text-white dark:border-emerald-500 dark:bg-emerald-500 dark:text-emerald-950'
  if (status === 'configured' || status === 'processing' || status === 'uploading') return 'border-sky-700 bg-sky-700 text-white dark:border-sky-500 dark:bg-sky-500 dark:text-sky-950'
  if (status === 'missing') return 'border-amber-700 bg-amber-600 text-white dark:border-amber-500 dark:bg-amber-500 dark:text-amber-950'
  return 'border-rose-700 bg-rose-700 text-white dark:border-rose-500 dark:bg-rose-500 dark:text-rose-950'
}

function MetricTile({
  title,
  value,
  detail,
  icon: Icon,
  accent,
}: {
  title: string
  value: string | number
  detail: string
  icon: ElementType
  accent: string
}) {
  return (
    <Card className="rounded-lg py-5 shadow-none">
      <CardContent className="px-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {title}
            </p>
            <p className="mt-2 text-2xl font-semibold tracking-normal">{value}</p>
            <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
          </div>
          <div className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-lg', accent)}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={cn('inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium', getStatusTone(status))}>
      {status}
    </span>
  )
}

function DocumentRow({ document }: { document: Document }) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_96px_80px_88px] items-center gap-3 border-b px-4 py-3 last:border-b-0">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium">{document.filename}</p>
        <p className="text-xs text-muted-foreground">{formatDate(document.updated_at || document.created_at)}</p>
      </div>
      <StatusBadge status={document.status} />
      <p className="text-sm text-muted-foreground">{document.chunk_count ?? 0} chunk</p>
      <p className="text-right text-xs uppercase text-muted-foreground">{document.file_type}</p>
    </div>
  )
}

export default function AdminPage() {
  const router = useRouter()
  const { user } = useAuthStore()
  const [overview, setOverview] = useState<AdminOverview | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadOverview = async () => {
    setIsLoading(true)
    setError(null)
    try {
      setOverview(await adminAPI.overview())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể tải dữ liệu admin')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (user?.role === 'admin') {
      loadOverview()
    } else {
      setIsLoading(false)
    }
  }, [user?.role])

  const failedDocumentText = useMemo(() => {
    if (!overview) return 'Chưa có dữ liệu'
    return overview.documents.failed === 0
      ? 'Không có lỗi xử lý'
      : `${overview.documents.failed} tài liệu lỗi`
  }, [overview])

  return (
    <AuthGuard>
      <div className="min-h-screen bg-background">
        <header className="sticky top-0 z-20 border-b bg-background/95 backdrop-blur">
          <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="icon" onClick={() => router.push('/conversation')} aria-label="Quay lại chat">
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <div>
                <h1 className="text-base font-semibold">Admin Dashboard</h1>
                <p className="text-xs text-muted-foreground">Giám sát vận hành hệ thống</p>
              </div>
            </div>
            <Button variant="outline" size="sm" onClick={loadOverview} disabled={isLoading || user?.role !== 'admin'}>
              {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              Làm mới
            </Button>
          </div>
        </header>

        <main className="mx-auto max-w-7xl px-4 py-6">
          {user?.role !== 'admin' ? (
            <div className="flex min-h-[60vh] items-center justify-center">
              <div className="max-w-md text-center">
                <Shield className="mx-auto mb-4 h-10 w-10 text-muted-foreground" />
                <h2 className="text-lg font-semibold">Bạn cần quyền Admin</h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  Dashboard này chỉ dành cho tài khoản quản trị để xem trạng thái hệ thống và đánh giá chất lượng.
                </p>
              </div>
            </div>
          ) : isLoading && !overview ? (
            <div className="flex min-h-[60vh] items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : error ? (
            <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
              {error}
            </div>
          ) : overview ? (
            <div className="space-y-6">
              <section className="grid gap-3 md:grid-cols-2">
                <MetricTile
                  title="Sức khỏe hệ thống"
                  value={overview.system.status}
                  detail={`${overview.system.services.length} thành phần được theo dõi`}
                  icon={Activity}
                  accent="bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                />
                <MetricTile
                  title="Tài liệu"
                  value={overview.documents.total}
                  detail={`${overview.documents.total_chunks} chunk, ${failedDocumentText}`}
                  icon={Database}
                  accent="bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300"
                />
              </section>

              <section className="grid gap-6 lg:grid-cols-[1fr_0.8fr]">
                <Card className="rounded-lg shadow-none">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Gauge className="h-4 w-4" />
                      Trạng thái thành phần
                    </CardTitle>
                    <CardDescription>Các dịch vụ chính mà pipeline phụ thuộc.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-hidden rounded-lg border">
                      {overview.system.services.map((service) => (
                        <div key={service.name} className="grid grid-cols-[minmax(0,1fr)_112px] items-center gap-3 border-b px-4 py-3 last:border-b-0">
                          <div className="min-w-0">
                            <p className="text-sm font-medium">{service.name}</p>
                          </div>
                          <StatusBadge status={service.status} />
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card className="rounded-lg shadow-none">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <MessageSquareText className="h-4 w-4" />
                      Hoạt động 24 giờ
                    </CardTitle>
                    <CardDescription>Tải sử dụng gần đây của chat.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between border-b pb-3">
                        <span className="text-sm text-muted-foreground">Hội thoại mới</span>
                        <span className="font-semibold">{overview.activity.conversations_24h}</span>
                      </div>
                      <div className="flex items-center justify-between border-b pb-3">
                        <span className="text-sm text-muted-foreground">Tin nhắn</span>
                        <span className="font-semibold">{overview.activity.messages_24h}</span>
                      </div>
                      <div className="flex items-center justify-between border-b pb-3">
                        <span className="text-sm text-muted-foreground">Câu trả lời AI</span>
                        <span className="font-semibold">{overview.activity.assistant_messages_24h}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Tổng hội thoại</span>
                        <span className="font-semibold">{overview.activity.total_conversations}</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </section>

              <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
                <Card className="rounded-lg shadow-none">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Database className="h-4 w-4" />
                      Tài liệu gần đây
                    </CardTitle>
                    <CardDescription>Trạng thái xử lý, số chunk và thời điểm cập nhật.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-hidden rounded-lg border">
                      {overview.documents.recent.length > 0 ? (
                        overview.documents.recent.map((document) => (
                          <DocumentRow key={document.id} document={document} />
                        ))
                      ) : (
                        <p className="p-4 text-sm text-muted-foreground">Chưa có tài liệu nào.</p>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card className="rounded-lg shadow-none">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <AlertTriangle className="h-4 w-4" />
                      Lỗi xử lý tài liệu
                    </CardTitle>
                    <CardDescription>File lỗi mới nhất và thông điệp từ pipeline.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {overview.documents.failed_items.length > 0 ? (
                        overview.documents.failed_items.map((document) => (
                          <div key={document.id} className="rounded-lg border p-3">
                            <div className="flex items-start justify-between gap-3">
                              <p className="min-w-0 truncate text-sm font-medium">{document.filename}</p>
                              <Badge variant="destructive">failed</Badge>
                            </div>
                            <p className="mt-2 line-clamp-3 text-xs text-muted-foreground">
                              {document.error_message || 'Không có thông điệp lỗi'}
                            </p>
                          </div>
                        ))
                      ) : (
                        <div className="flex items-center gap-2 rounded-lg border p-4 text-sm text-muted-foreground">
                          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                          Không có tài liệu lỗi.
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </section>

            </div>
          ) : null}
        </main>
      </div>
    </AuthGuard>
  )
}
