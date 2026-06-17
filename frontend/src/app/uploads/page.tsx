'use client'

import { useState, useCallback, useEffect, type ElementType } from 'react'
import { useRouter } from 'next/navigation'
import { useDocumentsUpload } from '@/lib/hooks/use-documents-upload'
import { Activity, AlertCircle, ArrowLeft, CheckCircle2, Clock3, Download, Eye, File, FileImage, FileText, Layers3, Loader2, Presentation, Trash2, Upload as UploadIcon, XCircle } from 'lucide-react'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { DocumentPreviewDialog } from '@/components/document-preview-dialog'
import { documentsAPI, type Document } from '@/lib/api/simple-client'
import { AuthGuard } from '@/components/auth/auth-guard'
import { useSourcesStore } from '@/lib/stores/sources-store'
import { useConversationStore } from '@/lib/stores/conversation-store'

// Modern, minimal colored file icons
const FILE_TYPES: Record<string, { icon: ElementType; color: string; bgColor: string }> = {
  pdf: {
    icon: FileText,
    color: 'text-rose-500 dark:text-rose-400',
    bgColor: 'bg-rose-500/10 border-rose-500/20 dark:bg-rose-500/5 dark:border-rose-500/10'
  },
  docx: {
    icon: FileText,
    color: 'text-blue-500 dark:text-blue-400',
    bgColor: 'bg-blue-500/10 border-blue-500/20 dark:bg-blue-500/5 dark:border-blue-500/10'
  },
  doc: {
    icon: FileText,
    color: 'text-blue-500 dark:text-blue-400',
    bgColor: 'bg-blue-500/10 border-blue-500/20 dark:bg-blue-500/5 dark:border-blue-500/10'
  },
  txt: {
    icon: FileText,
    color: 'text-zinc-500 dark:text-zinc-400',
    bgColor: 'bg-zinc-500/10 border-zinc-500/20 dark:bg-zinc-500/5 dark:border-zinc-500/10'
  },
  pptx: {
    icon: Presentation,
    color: 'text-amber-500 dark:text-amber-400',
    bgColor: 'bg-amber-500/10 border-amber-500/20 dark:bg-amber-500/5 dark:border-amber-500/10'
  },
  ppt: {
    icon: Presentation,
    color: 'text-amber-500 dark:text-amber-400',
    bgColor: 'bg-amber-500/10 border-amber-500/20 dark:bg-amber-500/5 dark:border-amber-500/10'
  },
  png: {
    icon: FileImage,
    color: 'text-emerald-500 dark:text-emerald-400',
    bgColor: 'bg-emerald-500/10 border-emerald-500/20 dark:bg-emerald-500/5 dark:border-emerald-500/10'
  },
  jpg: {
    icon: FileImage,
    color: 'text-emerald-500 dark:text-emerald-400',
    bgColor: 'bg-emerald-500/10 border-emerald-500/20 dark:bg-emerald-500/5 dark:border-emerald-500/10'
  },
  jpeg: {
    icon: FileImage,
    color: 'text-emerald-500 dark:text-emerald-400',
    bgColor: 'bg-emerald-500/10 border-emerald-500/20 dark:bg-emerald-500/5 dark:border-emerald-500/10'
  },
  default: {
    icon: File,
    color: 'text-zinc-400 dark:text-zinc-500',
    bgColor: 'bg-zinc-100 border-zinc-200 dark:bg-zinc-800 dark:border-zinc-700'
  },
}

const parseDocumentTime = (value?: string) => {
  if (!value) return null
  const normalized = value.endsWith('Z') ? value : `${value}Z`
  const parsed = Date.parse(normalized)
  return Number.isNaN(parsed) ? null : parsed
}

const formatElapsedTime = (seconds: number) => {
  if (seconds < 60) return `${Math.max(0, seconds).toFixed(0)}s`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.floor(seconds % 60)
  return `${minutes}m ${remainingSeconds}s`
}

type TrackingStepState = 'done' | 'active' | 'pending' | 'failed'

function getDocumentTracking(
  doc: Document,
  isUploading: boolean,
  now: number,
  activeUploadStarts: Record<string, number>,
  documentStarts: Record<string, number>
) {
  const isActiveUpload = isUploading || doc.status === 'uploading'
  const isProcessing = doc.status === 'processing'
  const isFailed = doc.status === 'failed'
  const isCancelled = doc.status === 'cancelled'
  const isCompleted = doc.status === 'completed'
  const startTime = isActiveUpload
    ? activeUploadStarts[doc.filename]
    : documentStarts[doc.id] || parseDocumentTime(doc.created_at)
  const elapsedSeconds = startTime ? Math.max(0, (now - startTime) / 1000) : 0

  if (isActiveUpload) {
    return {
      label: 'Đang tải file lên máy chủ',
      tone: 'text-sky-600 dark:text-sky-400',
      elapsedSeconds,
      steps: [
        { label: 'Tải lên', state: 'active' as TrackingStepState },
        { label: 'Trích xuất', state: 'pending' as TrackingStepState },
        { label: 'Lập chỉ mục', state: 'pending' as TrackingStepState },
      ],
    }
  }

  if (isProcessing) {
    return {
      label: 'Đang đọc nội dung và lập chỉ mục để có thể tra cứu',
      tone: 'text-amber-600 dark:text-amber-400',
      elapsedSeconds,
      steps: [
        { label: 'Tải lên', state: 'done' as TrackingStepState },
        { label: 'Đọc nội dung', state: 'active' as TrackingStepState },
        { label: 'Sẵn sàng tra cứu', state: 'pending' as TrackingStepState },
      ],
    }
  }

  if (isFailed) {
    return {
      label: doc.error_message || 'Xử lý tài liệu thất bại',
      tone: 'text-rose-600 dark:text-rose-400',
      elapsedSeconds,
      steps: [
        { label: 'Tải lên', state: 'done' as TrackingStepState },
        { label: 'Đọc nội dung', state: 'failed' as TrackingStepState },
        { label: 'Sẵn sàng tra cứu', state: 'pending' as TrackingStepState },
      ],
    }
  }

  if (isCancelled) {
    return {
      label: 'Đã dừng xử lý theo yêu cầu của bạn',
      tone: 'text-zinc-600 dark:text-zinc-400',
      elapsedSeconds,
      steps: [
        { label: 'Tải lên', state: 'done' as TrackingStepState },
        { label: 'Đọc nội dung', state: 'failed' as TrackingStepState },
        { label: 'Sẵn sàng tra cứu', state: 'pending' as TrackingStepState },
      ],
    }
  }

  return {
    label: isCompleted ? 'Sẵn sàng để tra cứu' : 'Chờ xử lý',
    tone: isCompleted ? 'text-emerald-600 dark:text-emerald-400' : 'text-muted-foreground',
    elapsedSeconds,
    steps: [
      { label: 'Tải lên', state: isCompleted ? 'done' as TrackingStepState : 'pending' as TrackingStepState },
      { label: 'Đọc nội dung', state: isCompleted ? 'done' as TrackingStepState : 'pending' as TrackingStepState },
      { label: 'Sẵn sàng tra cứu', state: isCompleted ? 'done' as TrackingStepState : 'pending' as TrackingStepState },
    ],
  }
}

function TrackingStep({ label, state }: { label: string; state: TrackingStepState }) {
  return (
    <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
      <span
        className={cn(
          'flex h-4 w-4 items-center justify-center rounded-full border',
          state === 'done' && 'border-emerald-500 bg-emerald-500 text-white',
          state === 'active' && 'border-amber-500 bg-amber-500/10 text-amber-600 dark:text-amber-400',
          state === 'failed' && 'border-rose-500 bg-rose-500 text-white',
          state === 'pending' && 'border-border bg-background'
        )}
      >
        {state === 'done' ? (
          <CheckCircle2 className="h-3 w-3" />
        ) : state === 'failed' ? (
          <AlertCircle className="h-3 w-3" />
        ) : state === 'active' ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : null}
      </span>
      <span className={cn(state === 'active' && 'font-medium text-foreground')}>{label}</span>
    </div>
  )
}

export default function UploadsPage() {
  const router = useRouter()
  const resetSources = useSourcesStore((state) => state.reset)
  const clearActiveConversation = useConversationStore((state) => state.clearActiveConversation)
  const documents = useDocumentsUpload()
  const [isDragging, setIsDragging] = useState(false)
  const [now, setNow] = useState<number>(Date.now())

  // Preview Dialog States
  const [previewDocId, setPreviewDocId] = useState<string | null>(null)
  const [previewFilename, setPreviewFilename] = useState<string>('')
  const [isPreviewOpen, setIsPreviewOpen] = useState(false)
  const [documentToDelete, setDocumentToDelete] = useState<Document | null>(null)
  const [isDeletingDocument, setIsDeletingDocument] = useState(false)
  const [documentToCancel, setDocumentToCancel] = useState<Document | null>(null)
  const [isCancellingDocument, setIsCancellingDocument] = useState(false)

  useEffect(() => {
    const interval = setInterval(() => {
      setNow(Date.now())
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback(() => {
    setIsDragging(false)
  }, [])

  const uploadFile = async (file: File) => {
    const allowedTypes = ['pdf', 'docx', 'doc', 'txt', 'png', 'jpg', 'jpeg', 'tiff', 'pptx', 'ppt']
    const ext = file.name.split('.').pop()?.toLowerCase() || ''

    if (!allowedTypes.includes(ext)) {
      alert(`Loại file không được hỗ trợ. Vui lòng tải lên: ${allowedTypes.join(', ')}`)
      return
    }

    if (file.size > 50 * 1024 * 1024) {
      alert('Kích thước file không được vượt quá 50MB')
      return
    }

    try {
      await documents.uploadDocument(file)
    } catch (err) {
      // Error handled by UI feedback
    }
  }

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      await uploadFile(files[0])
    }
  }, [documents])

  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      await uploadFile(file)
    }
    e.target.value = ''
  }, [uploadFile])

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const handleConfirmDelete = async () => {
    if (!documentToDelete) return

    setIsDeletingDocument(true)
    try {
      await documents.deleteDocument(documentToDelete.id)
      setDocumentToDelete(null)
    } finally {
      setIsDeletingDocument(false)
    }
  }

  const handleConfirmCancel = async () => {
    if (!documentToCancel) return

    setIsCancellingDocument(true)
    try {
      await documents.cancelDocument(documentToCancel.id)
      setDocumentToCancel(null)
    } finally {
      setIsCancellingDocument(false)
    }
  }

  const totalDocuments = documents.documents.length
  const activeUploadItems = Object.values(documents.activeUploads)
  const uploadingCount = activeUploadItems.length + documents.documents.filter(
    (doc) => documents.isUploading(doc.filename) || doc.status === 'uploading'
  ).length
  const processingCount = documents.documents.filter((doc) => doc.status === 'processing').length
  const completedCount = documents.documents.filter((doc) => doc.status === 'completed').length
  const failedCount = documents.documents.filter((doc) => doc.status === 'failed').length
  const cancelledCount = documents.documents.filter((doc) => doc.status === 'cancelled').length
  const activeCount = uploadingCount + processingCount
  const indexedChunks = documents.documents.reduce((total, doc) => total + (doc.chunk_count ?? 0), 0)
  const shouldShowTrackingPanel = totalDocuments > 0 && (activeCount > 0 || failedCount > 0 || cancelledCount > 0)
  const latestUpdatedAt = documents.documents
    .map((doc) => parseDocumentTime(doc.updated_at || doc.created_at))
    .filter((timestamp): timestamp is number => timestamp !== null)
    .sort((a, b) => b - a)[0]

  const handleBackToChat = () => {
    clearActiveConversation()
    resetSources()
    router.push('/conversation')
  }

  return (
    <AuthGuard>
      <div className="flex flex-col h-screen bg-background">
        {/* Header */}
        <div className="h-14 border-b flex items-center px-4 shrink-0">
          <Button
            variant="ghost"
            size="sm"
            className="gap-2"
            onClick={handleBackToChat}
          >
            <ArrowLeft className="w-4 h-4" />
            Quay lại chat
          </Button>
        </div>

        {/* Main Content */}
        <div className="flex-1 overflow-hidden">
          <div className="mx-auto grid h-full max-w-7xl grid-rows-[auto_1fr] lg:grid-cols-[360px_minmax(0,1fr)] lg:grid-rows-1">
            {/* Page Header */}
            <aside className="border-b lg:border-b-0 lg:border-r">
              <div className="p-6 border-b">
                <h1 className="text-2xl font-bold mb-1">Tài liệu</h1>
                <p className="text-sm text-muted-foreground">
                  Tải lên, theo dõi xử lý và dùng tài liệu để tra cứu trong chat.
                </p>
              </div>

              {/* Upload Zone */}
              <div className="p-6 border-b">
                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  className={cn(
                    'relative border-2 border-dashed rounded-xl text-center transition-all',
                    'p-6 lg:p-8',
                    isDragging
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:border-primary/50 hover:bg-muted/30'
                  )}
                >
                  <input
                    type="file"
                    id="file-upload"
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    onChange={handleFileSelect}
                    accept=".pdf,.docx,.doc,.txt,.png,.jpg,.jpeg,.tiff,.pptx,.ppt"
                  />
                  <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-3">
                    <UploadIcon className={cn(
                      'h-6 w-6',
                      isDragging ? 'text-primary' : 'text-muted-foreground'
                    )} />
                  </div>
                  <h3 className="text-base font-semibold mb-0.5">
                    {isDragging ? 'Thả file vào đây' : totalDocuments > 0 ? 'Tải thêm tài liệu' : 'Kéo thả file để tải lên'}
                  </h3>
                  <p className="text-xs text-muted-foreground mb-3">
                    hoặc click để chọn file từ máy tính
                  </p>
                  <p className="text-[10px] leading-4 text-muted-foreground">
                    PDF, DOCX, DOC, TXT, PNG, JPG, JPEG, TIFF, PPTX, PPT. Tối đa 50MB.
                  </p>
                </div>
              </div>

              {/* Error */}
              {documents.error && (
                <div className="px-6 py-3 border-b">
                  <div className="bg-destructive/10 text-destructive text-xs px-4 py-2.5 rounded-lg">
                    {documents.error}
                  </div>
                </div>
              )}

              {/* Processing Tracking */}
              <div className="p-6">
                <div className="flex items-center gap-2">
                  <Activity className="h-4 w-4 text-primary" />
                  <h2 className="text-sm font-semibold">Tiến trình xử lý</h2>
                </div>

                {shouldShowTrackingPanel ? (
                  <div className="mt-3 space-y-4">
                    <p className="text-xs text-muted-foreground">
                      Bạn có thể rời trang này; hệ thống vẫn tiếp tục xử lý tài liệu.
                      {latestUpdatedAt ? ` Cập nhật gần nhất: ${new Date(latestUpdatedAt).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}.` : ''}
                    </p>

                    <div className="grid grid-cols-2 gap-2">
                      <div className="rounded-lg border bg-background px-3 py-2">
                        <p className="text-[11px] text-muted-foreground">Đang tải</p>
                        <p className="mt-1 text-lg font-semibold text-sky-600 dark:text-sky-400">{uploadingCount}</p>
                      </div>
                      <div className="rounded-lg border bg-background px-3 py-2">
                        <p className="text-[11px] text-muted-foreground">Đang xử lý</p>
                        <p className="mt-1 text-lg font-semibold text-amber-600 dark:text-amber-400">{processingCount}</p>
                      </div>
                      <div className="rounded-lg border bg-background px-3 py-2">
                        <p className="text-[11px] text-muted-foreground">Lỗi</p>
                        <p className="mt-1 text-lg font-semibold text-rose-600 dark:text-rose-400">{failedCount}</p>
                      </div>
                      <div className="rounded-lg border bg-background px-3 py-2">
                        <p className="text-[11px] text-muted-foreground">Đã dừng</p>
                        <p className="mt-1 text-lg font-semibold text-zinc-600 dark:text-zinc-400">{cancelledCount}</p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="mt-3 rounded-lg border bg-muted/20 px-3 py-3">
                    <p className="text-xs text-muted-foreground">
                      {totalDocuments === 0
                        ? 'Chưa có tài liệu nào đang xử lý.'
                        : 'Không có tài liệu nào đang xử lý.'}
                    </p>
                  </div>
                )}

                {totalDocuments > 0 && (
                  <div className="mt-4 grid grid-cols-2 gap-2">
                    <div className="rounded-lg border bg-background px-3 py-2">
                      <p className="text-[11px] text-muted-foreground">Sẵn sàng</p>
                      <p className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400">{completedCount}</p>
                    </div>
                    <div className="rounded-lg border bg-background px-3 py-2">
                      <p className="text-[11px] text-muted-foreground">Đã lập chỉ mục</p>
                      <p className="mt-1 text-lg font-semibold">{indexedChunks}</p>
                    </div>
                  </div>
                )}
              </div>
            </aside>

            <section className="min-h-0 overflow-hidden">
              <div className="flex h-full flex-col">
                <div className="border-b p-6">
                  <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
                    <div>
                      <h2 className="text-lg font-semibold">Danh sách tài liệu</h2>
                      <p className="text-sm text-muted-foreground">
                        {totalDocuments} tài liệu trong thư viện của bạn.
                      </p>
                    </div>
                    {totalDocuments > 0 && (
                      <p className="text-xs text-muted-foreground">
                        {completedCount} sẵn sàng
                        {indexedChunks > 0 ? ` · ${indexedChunks} đoạn đã lập chỉ mục` : ''}
                      </p>
                    )}
                  </div>
                </div>

                {/* Documents List */}
                <div className="flex-1 overflow-y-auto">
                  <div className="p-6">
                {documents.isLoading && documents.documents.length === 0 && activeUploadItems.length === 0 ? (
                  <div className="flex items-center justify-center h-48">
                    <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                  </div>
                ) : documents.documents.length === 0 && activeUploadItems.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-48 text-center">
                    <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center mb-2">
                      <FileText className="w-5 h-5 text-muted-foreground" />
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Chưa có tài liệu nào
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Tải lên tài liệu để bắt đầu
                    </p>
                  </div>
                ) : (
                  <div className="space-y-1.5">
                    {activeUploadItems.map((upload) => {
                      const fileType = FILE_TYPES[upload.file_type.toLowerCase()] || FILE_TYPES.default
                      const Icon = fileType.icon
                      const elapsedSeconds = Math.max(0, (now - upload.started_at) / 1000)

                      return (
                        <div
                          key={upload.filename}
                          className="flex flex-col gap-3 rounded-lg border border-sky-500/20 bg-sky-500/5 p-3 transition-all"
                        >
                          <div className="flex items-center gap-3">
                            <div className={cn(
                              "w-10 h-10 rounded-lg flex items-center justify-center shrink-0 border",
                              fileType.bgColor
                            )}>
                              <Icon className={cn('w-5 h-5', fileType.color)} />
                            </div>

                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium truncate text-foreground">
                                {upload.filename}
                              </p>
                              <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1.5 flex-wrap">
                                <span>{formatFileSize(upload.file_size)}</span>
                                <span className="text-[10px] opacity-40">•</span>
                                <span>Đang tải lên {formatElapsedTime(elapsedSeconds)}</span>
                              </p>
                            </div>

                            <Button
                              variant="ghost"
                              size="sm"
                              className="shrink-0 gap-1.5 text-sky-700 hover:bg-sky-500/10 hover:text-sky-800 dark:text-sky-300 dark:hover:text-sky-200"
                              onClick={() => documents.cancelUpload(upload.filename)}
                            >
                              <XCircle className="h-4 w-4" />
                              Dừng
                            </Button>
                          </div>

                          <div className="space-y-2 border-t pt-3">
                            <div className="flex items-center justify-between gap-3">
                              <p className="truncate text-xs font-medium text-sky-600 dark:text-sky-400">
                                Đang tải file lên máy chủ
                              </p>
                              <span className="shrink-0 text-[11px] text-muted-foreground">
                                Có thể dừng
                              </span>
                            </div>
                            <div aria-hidden="true" className="h-1.5 overflow-hidden rounded-full bg-muted">
                              <div className="h-full w-1/3 animate-pulse rounded-full bg-sky-500" />
                            </div>
                            <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                              <TrackingStep label="Tải lên" state="active" />
                              <TrackingStep label="Đọc nội dung" state="pending" />
                              <TrackingStep label="Sẵn sàng tra cứu" state="pending" />
                            </div>
                          </div>
                        </div>
                      )
                    })}

                    {documents.documents.map((doc) => {
                      const fileType = FILE_TYPES[doc.file_type.toLowerCase()] || FILE_TYPES.default
                      const Icon = fileType.icon
                      const uploading = documents.isUploading(doc.filename)
                      const isCompleted = doc.status === 'completed'
                      const isCancelled = doc.status === 'cancelled'
                      const uploadDuration = documents.uploadDurations[doc.id] || documents.uploadDurations[doc.filename]
                      const tracking = getDocumentTracking(
                        doc,
                        uploading,
                        now,
                        documents.activeUploadStarts,
                        documents.documentStarts
                      )
                      const isActivelyTracked = uploading || doc.status === 'uploading' || doc.status === 'processing'

                      const ext = doc.file_type.toLowerCase()
                      const isWordOrPpt = ext === 'doc' || ext === 'docx' || ext === 'ppt' || ext === 'pptx'

                      return (
                        <div
                          key={doc.id}
                          onClick={() => {
                            if (isCompleted && !uploading) {
                              if (isWordOrPpt) {
                                const downloadUrl = documentsAPI.getDownloadUrl(doc.id)
                                const link = document.createElement('a')
                                link.href = downloadUrl
                                link.setAttribute('download', doc.filename)
                                document.body.appendChild(link)
                                link.click()
                                document.body.removeChild(link)
                              } else {
                                setPreviewDocId(doc.id)
                                setPreviewFilename(doc.filename)
                                setIsPreviewOpen(true)
                              }
                            }
                          }}
                          className={cn(
                            'flex flex-col gap-3 rounded-lg border p-3 transition-all select-none group',
                            uploading && 'bg-primary/5 border-primary/20',
                            !uploading && isCompleted && 'hover:bg-muted/50 border-border cursor-pointer hover:border-primary/20',
                            !uploading && !isCompleted && 'border-border bg-muted/10 opacity-70'
                          )}
                        >
                          <div className="flex items-center gap-3">
                            {/* File Icon Container */}
                            <div className={cn(
                              "w-10 h-10 rounded-lg flex items-center justify-center shrink-0 border transition-transform duration-200 group-hover:scale-105",
                              fileType.bgColor
                            )}>
                              <Icon className={cn('w-5 h-5', fileType.color)} />
                            </div>

                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium truncate text-foreground group-hover:text-primary transition-colors">
                                {doc.filename}
                              </p>
                              <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1.5 flex-wrap">
                                <span>{formatFileSize(doc.file_size)}</span>
                                {doc.chunk_count !== undefined && doc.chunk_count > 0 && (
                                  <>
                                    <span className="text-[10px] opacity-40">•</span>
                                    <span className="inline-flex items-center gap-1">
                                      <Layers3 className="h-3 w-3" />
                                      {doc.chunk_count} đoạn đã lập chỉ mục
                                    </span>
                                  </>
                                )}
                                {uploadDuration !== undefined && (
                                  <>
                                    <span className="text-[10px] opacity-40">•</span>
                                    <span>Hoàn tất sau {uploadDuration.toFixed(1)}s</span>
                                  </>
                                )}
                              </p>
                            </div>

                            {/* Status/Actions Container */}
                            <div className="shrink-0 flex items-center gap-3">

                              {/* Active Loaders & Error states */}
                              {(uploading || doc.status === 'uploading' || doc.status === 'processing') ? (
                                <span className={cn("flex items-center gap-1.5 text-xs font-medium", tracking.tone)}>
                                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                  {doc.status === 'processing' ? 'Đang xử lý' : 'Đang tải'}
                                  {tracking.elapsedSeconds ? ` (${formatElapsedTime(tracking.elapsedSeconds)})` : ''}
                                </span>
                              ) : doc.status === 'failed' ? (
                                <span
                                  className="text-xs text-rose-500 bg-rose-500/10 px-2 py-0.5 rounded-full font-medium cursor-help"
                                  title={doc.error_message || "Lỗi xử lý tài liệu"}
                                >
                                  Thất bại
                                </span>
                              ) : isCancelled ? (
                                <span className="flex items-center gap-1.5 text-xs font-medium text-zinc-600 dark:text-zinc-400">
                                  <XCircle className="h-3.5 w-3.5" />
                                  Đã dừng
                                </span>
                              ) : isCompleted ? (
                                <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                                  <CheckCircle2 className="h-3.5 w-3.5" />
                                  Sẵn sàng
                                </span>
                              ) : (
                                <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                                  <Clock3 className="h-3.5 w-3.5" />
                                  Chờ xử lý
                                </span>
                              )}

                              {/* Action Hover Helper Icons */}
                              {isCompleted && !uploading && (
                                <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center text-muted-foreground mr-1">
                                  {isWordOrPpt ? (
                                    <Download className="w-4 h-4 hover:text-foreground" />
                                  ) : (
                                    <Eye className="w-4 h-4 hover:text-foreground" />
                                  )}
                                </div>
                              )}

                              {(doc.status === 'uploading' || doc.status === 'processing') && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className={cn(
                                    "h-8 shrink-0 gap-1.5",
                                    doc.status === 'uploading'
                                      ? "text-sky-700 hover:bg-sky-500/10 hover:text-sky-800 dark:text-sky-300 dark:hover:text-sky-200"
                                      : "text-amber-700 hover:bg-amber-500/10 hover:text-amber-800 dark:text-amber-300 dark:hover:text-amber-200"
                                  )}
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    setDocumentToCancel(doc)
                                  }}
                                >
                                  <XCircle className="h-4 w-4" />
                                  Dừng
                                </Button>
                              )}

                              {/* Delete Button */}
                              {!uploading && doc.status !== 'uploading' && doc.status !== 'processing' && (
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="w-8 h-8 rounded-lg shrink-0 relative z-10 opacity-100 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all md:opacity-0 md:group-hover:opacity-100"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    setDocumentToDelete(doc)
                                  }}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              )}
                            </div>
                          </div>

                          {(isActivelyTracked || doc.status === 'failed' || doc.status === 'cancelled') && (
                            <div className="space-y-2 border-t pt-3">
                              <div className="flex items-center justify-between gap-3">
                                <p className={cn("truncate text-xs font-medium", tracking.tone)}>
                                  {tracking.label}
                                </p>
                                {tracking.elapsedSeconds > 0 && (
                                  <span className="shrink-0 text-[11px] text-muted-foreground">
                                    {formatElapsedTime(tracking.elapsedSeconds)}
                                  </span>
                                )}
                              </div>
                              <div
                                aria-hidden="true"
                                className={cn(
                                  'h-1.5 overflow-hidden rounded-full bg-muted',
                                  doc.status === 'failed' && 'bg-rose-500/15',
                                  doc.status === 'cancelled' && 'bg-zinc-500/15'
                                )}
                              >
                                <div
                                  className={cn(
                                    'h-full rounded-full',
                                    doc.status === 'failed' && 'w-full bg-rose-500',
                                    doc.status === 'cancelled' && 'w-full bg-zinc-500',
                                    (uploading || doc.status === 'uploading') && 'w-1/3 animate-pulse bg-sky-500',
                                    doc.status === 'processing' && 'w-2/3 animate-pulse bg-amber-500'
                                  )}
                                />
                              </div>
                              <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                                {tracking.steps.map((step) => (
                                  <TrackingStep key={step.label} label={step.label} state={step.state} />
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                    )}
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>

        {/* Document Preview Dialog Component */}
        <DocumentPreviewDialog
          documentId={previewDocId}
          filename={previewFilename}
          isOpen={isPreviewOpen}
          onClose={() => setIsPreviewOpen(false)}
        />

        <AlertDialog
          open={documentToDelete !== null}
          onOpenChange={(open) => {
            if (!open && !isDeletingDocument) {
              setDocumentToDelete(null)
            }
          }}
        >
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Xoá tài liệu?</AlertDialogTitle>
              <AlertDialogDescription>
                Tài liệu “{documentToDelete?.filename}” sẽ bị xoá khỏi thư viện và không còn được dùng để tra cứu trong chat.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={isDeletingDocument}>Huỷ</AlertDialogCancel>
              <AlertDialogAction
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                disabled={isDeletingDocument}
                onClick={(event) => {
                  event.preventDefault()
                  handleConfirmDelete()
                }}
              >
                {isDeletingDocument ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Đang xoá
                  </>
                ) : (
                  'Xoá tài liệu'
                )}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        <AlertDialog
          open={documentToCancel !== null}
          onOpenChange={(open) => {
            if (!open && !isCancellingDocument) {
              setDocumentToCancel(null)
            }
          }}
        >
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Dừng xử lý tài liệu?</AlertDialogTitle>
              <AlertDialogDescription>
                Hệ thống sẽ dừng tác vụ xử lý của “{documentToCancel?.filename}” và xoá dữ liệu tạm đã tạo trong quá trình lập chỉ mục.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={isCancellingDocument}>Huỷ</AlertDialogCancel>
              <AlertDialogAction
                className="bg-amber-600 text-white hover:bg-amber-700 dark:bg-amber-500 dark:text-amber-950 dark:hover:bg-amber-400"
                disabled={isCancellingDocument}
                onClick={(event) => {
                  event.preventDefault()
                  handleConfirmCancel()
                }}
              >
                {isCancellingDocument ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Đang dừng
                  </>
                ) : (
                  'Dừng xử lý'
                )}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </AuthGuard>
  )
}
