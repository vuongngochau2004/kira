'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useDocumentsUpload } from '@/lib/hooks/use-documents-upload'
import { useAuthStore } from '@/lib/stores/auth-store'
import { Sparkles, ArrowLeft, Upload as UploadIcon, FileText, File, Trash2, Loader2, Eye, Download, FileImage, Presentation } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { DocumentPreviewDialog } from '@/components/document-preview-dialog'
import { documentsAPI } from '@/lib/api/simple-client'

// Modern, minimal colored file icons
const FILE_TYPES: Record<string, { icon: any; color: string; bgColor: string }> = {
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

export default function UploadsPage() {
  const router = useRouter()
  const { isAuthenticated } = useAuthStore()
  const documents = useDocumentsUpload()
  const [mounted, setMounted] = useState(false)
  const [isDragging, setIsDragging] = useState(false)

  // Preview Dialog States
  const [previewDocId, setPreviewDocId] = useState<string | null>(null)
  const [previewFilename, setPreviewFilename] = useState<string>('')
  const [isPreviewOpen, setIsPreviewOpen] = useState(false)

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
              Quản lý tài liệu của bạn. Nhấp để xem hoặc tải xuống.
            </p>
          </div>

          {/* Upload Zone */}
          <div className="p-6 border-b">
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={cn(
                'relative border-2 border-dashed rounded-xl p-10 text-center transition-all',
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
              <div className="w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-3">
                <UploadIcon className={cn(
                  'w-7 h-7',
                  isDragging ? 'text-primary' : 'text-muted-foreground'
                )} />
              </div>
              <h3 className="text-base font-semibold mb-0.5">
                {isDragging ? 'Thả file vào đây' : 'Kéo thả file để tải lên'}
              </h3>
              <p className="text-xs text-muted-foreground mb-3">
                hoặc click để chọn file từ máy tính
              </p>
              <p className="text-[10px] text-muted-foreground">
                Hỗ trợ: PDF, DOCX, DOC, TXT, PNG, JPG, JPEG, TIFF, PPTX, PPT (tối đa 50MB)
              </p>
            </div>
          </div>

          {/* Error */}
          {documents.error && (
            <div className="px-6 py-2">
              <div className="bg-destructive/10 text-destructive text-xs px-4 py-2.5 rounded-lg">
                {documents.error}
              </div>
            </div>
          )}

          {/* Documents List */}
          <div className="flex-1 overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
                  Danh sách tài liệu ({documents.documents.length})
                </h2>
              </div>

              {documents.isLoading && documents.documents.length === 0 ? (
                <div className="flex items-center justify-center h-48">
                  <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                </div>
              ) : documents.documents.length === 0 ? (
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
                  {documents.documents.map((doc) => {
                    const fileType = FILE_TYPES[doc.file_type.toLowerCase()] || FILE_TYPES.default
                    const Icon = fileType.icon
                    const uploading = documents.isUploading(doc.filename)
                    const isCompleted = doc.status === 'completed'
                    
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
                          'flex items-center gap-3 p-3 rounded-xl border transition-all select-none group',
                          uploading && 'bg-primary/5 border-primary/20',
                          !uploading && isCompleted && 'hover:bg-muted/50 border-border cursor-pointer hover:border-primary/20',
                          !uploading && !isCompleted && 'border-border bg-muted/10 opacity-70'
                        )}
                      >
                        {/* File Icon Container */}
                        <div className={cn(
                          "w-10 h-10 rounded-lg flex items-center justify-center shrink-0 border transition-transform duration-200 group-hover:scale-105",
                          fileType.bgColor
                        )}>
                          <Icon className={cn('w-5 h-5', fileType.color)} />
                        </div>

                        {/* File Info */}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate text-foreground group-hover:text-primary transition-colors">
                            {doc.filename}
                          </p>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {formatFileSize(doc.file_size)}
                          </p>
                        </div>

                        {/* Status/Actions Container */}
                        <div className="shrink-0 flex items-center gap-3">
                          
                          {/* Active Loaders & Error states */}
                          {(uploading || doc.status === 'uploading') ? (
                            <span className="flex items-center gap-1.5 text-xs text-blue-500 font-medium">
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              Đang tải
                            </span>
                          ) : doc.status === 'processing' ? (
                            <span className="flex items-center gap-1.5 text-xs text-amber-500 font-medium">
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              Đang xử lý
                            </span>
                          ) : doc.status === 'failed' ? (
                            <span 
                              className="text-xs text-rose-500 bg-rose-500/10 px-2 py-0.5 rounded-full font-medium cursor-help"
                              title={doc.error_message || "Lỗi xử lý tài liệu"}
                            >
                              Thất bại
                            </span>
                          ) : null}

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

                          {/* Delete Button */}
                          {!uploading && doc.status !== 'processing' && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="w-8 h-8 rounded-lg shrink-0 relative z-10 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all"
                              onClick={(e) => {
                                e.stopPropagation()
                                if (confirm(`Bạn có chắc chắn muốn xóa tài liệu "${doc.filename}"?`)) {
                                  documents.deleteDocument(doc.id)
                                }
                              }}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Document Preview Dialog Component */}
      <DocumentPreviewDialog
        documentId={previewDocId}
        filename={previewFilename}
        isOpen={isPreviewOpen}
        onClose={() => setIsPreviewOpen(false)}
      />
    </div>
  )
}
