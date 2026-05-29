'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useDocumentsUpload } from '@/lib/hooks/use-documents-upload'
import { useAuthStore } from '@/lib/stores/auth-store'
import { Sparkles, ArrowLeft, Upload as UploadIcon, FileText, File, Trash2, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
// File type icons with colors
const FILE_TYPES: Record<string, { icon: typeof File; color: string }> = {
  pdf: { icon: FileText, color: 'text-red-500' },
  docx: { icon: FileText, color: 'text-blue-500' },
  doc: { icon: FileText, color: 'text-blue-500' },
  txt: { icon: FileText, color: 'text-gray-500' },
  pptx: { icon: FileText, color: 'text-orange-500' },
  ppt: { icon: FileText, color: 'text-orange-500' },
  png: { icon: FileText, color: 'text-green-500' },
  jpg: { icon: FileText, color: 'text-green-500' },
  jpeg: { icon: FileText, color: 'text-green-500' },
  default: { icon: File, color: 'text-gray-400' },
}

export default function UploadsPage() {
  const router = useRouter()
  const { isAuthenticated } = useAuthStore()
  const documents = useDocumentsUpload()
  const [mounted, setMounted] = useState(false)
  const [isDragging, setIsDragging] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (mounted && !isAuthenticated) {
      router.push('/')
    }
  }, [mounted, isAuthenticated, router])

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
      console.error('Upload failed:', err)
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

  if (!mounted || !isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-zinc-950 text-white">
        <div className="text-center">
          <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4 mx-auto animate-pulse">
            <Sparkles className="w-6 h-6 text-primary" />
          </div>
          <h2 className="text-xl font-bold mb-1">K.I.R.A</h2>
          <p className="text-xs text-zinc-500">Đang khởi tạo...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Header */}
      <div className="h-14 border-b flex items-center px-4 shrink-0">
        <Button
          variant="ghost"
          size="sm"
          className="gap-2"
          onClick={() => router.push('/chat')}
        >
          <ArrowLeft className="w-4 h-4" />
          Quay lại chat
        </Button>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        <div className="max-w-4xl mx-auto h-full flex flex-col">
          {/* Page Header */}
          <div className="p-6 border-b">
            <h1 className="text-2xl font-bold mb-1">Tài liệu</h1>
            <p className="text-sm text-muted-foreground">
              Quản lý và tải lên tài liệu của bạn
            </p>
          </div>

          {/* Upload Zone */}
          <div className="p-6 border-b">
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={cn(
                'relative border-2 border-dashed rounded-xl p-12 text-center transition-all',
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
              <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                <UploadIcon className={cn(
                  'w-8 h-8',
                  isDragging ? 'text-primary' : 'text-muted-foreground'
                )} />
              </div>
              <h3 className="text-lg font-semibold mb-1">
                {isDragging ? 'Thả file vào đây' : 'Kéo thả file để tải lên'}
              </h3>
              <p className="text-sm text-muted-foreground mb-4">
                hoặc click để chọn file từ máy tính
              </p>
              <p className="text-xs text-muted-foreground">
                Hỗ trợ: PDF, DOCX, DOC, TXT, PNG, JPG, JPEG, TIFF, PPTX, PPT (tối đa 50MB)
              </p>
            </div>
          </div>

          {/* Error */}
          {documents.error && (
            <div className="px-6 py-3">
              <div className="bg-destructive/10 text-destructive text-sm px-4 py-3 rounded-lg">
                {documents.error}
              </div>
            </div>
          )}

          {/* Documents List */}
          <div className="flex-1 overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">
                  Đã tải lên ({documents.documents.length})
                </h2>
              </div>

              {documents.isLoading && documents.documents.length === 0 ? (
                <div className="flex items-center justify-center h-48">
                  <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                </div>
              ) : documents.documents.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-48 text-center">
                  <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-3">
                    <FileText className="w-6 h-6 text-muted-foreground" />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Chưa có tài liệu nào
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Tải lên tài liệu để bắt đầu
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {documents.documents.map((doc) => {
                    const fileType = FILE_TYPES[doc.file_type] || FILE_TYPES.default
                    const Icon = fileType.icon
                    const uploading = documents.isUploading(doc.filename)

                    return (
                      <div
                        key={doc.id}
                        className={cn(
                          'flex items-center gap-4 p-4 rounded-xl border transition-all',
                          uploading && 'bg-primary/5 border-primary/20',
                          !uploading && 'hover:bg-muted/50 border-border'
                        )}
                      >
                        {/* File Icon */}
                        <div className="shrink-0">
                          <Icon className={cn('w-10 h-10', fileType.color)} />
                        </div>

                        {/* Info */}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{doc.filename}</p>
                          <p className="text-xs text-muted-foreground">
                            {formatFileSize(doc.file_size)}
                          </p>
                        </div>

                        {/* Status Indicator */}
                        <div className="shrink-0 flex items-center gap-2 text-xs">
                          {uploading || doc.status === 'uploading' ? (
                            <span className="flex items-center gap-1.5 text-blue-500 bg-blue-500/10 px-2.5 py-1 rounded-full font-medium">
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              Đang tải lên
                            </span>
                          ) : doc.status === 'processing' ? (
                            <span className="flex items-center gap-1.5 text-amber-500 bg-amber-500/10 px-2.5 py-1 rounded-full font-medium">
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              Đang xử lý
                            </span>
                          ) : doc.status === 'completed' ? (
                            <span className="flex items-center gap-1.5 text-emerald-500 bg-emerald-500/10 px-2.5 py-1 rounded-full font-medium">
                              ✓ Thành công
                            </span>
                          ) : (
                            <span 
                              className="flex items-center gap-1.5 text-rose-500 bg-rose-500/10 px-2.5 py-1 rounded-full font-medium cursor-help"
                              title={doc.error_message || "Lỗi xử lý tài liệu"}
                            >
                              ✕ Thất bại
                            </span>
                          )}
                        </div>

                        {/* Actions */}
                        {!uploading && doc.status !== 'processing' && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="shrink-0"
                            onClick={() => documents.deleteDocument(doc.id)}
                          >
                            <Trash2 className="w-4 h-4 text-destructive" />
                          </Button>
                        )}

                        {(uploading || doc.status === 'processing') && (
                          <div className="w-9 h-9 flex items-center justify-center shrink-0">
                            <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
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
      </div>
    </div>
  )
}
