'use client'

import { useCallback, useState } from 'react'
import { Upload, FileText, Trash2, Loader2, File, CheckCircle, XCircle, Clock } from 'lucide-react'
import { Document } from '@/lib/api/simple-client'
import { cn } from '@/lib/utils'

interface DocumentUploadProps {
  documents: Document[]
  isLoading: boolean
  onUpload: (file: File) => Promise<Document | void>
  onDelete: (id: string) => Promise<void>
  isUploading: (filename: string) => boolean
  error?: string | null
}

// File type icons
const FILE_ICONS: Record<string, typeof File> = {
  pdf: FileText,
  docx: FileText,
  doc: FileText,
  txt: FileText,
  default: File,
}

// Status configs
const STATUS_CONFIG = {
  pending: { icon: Clock, color: 'text-yellow-600', bg: 'bg-yellow-50 dark:bg-yellow-900/20', label: 'Chờ xử lý' },
  processing: { icon: Loader2, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20', label: 'Đang xử lý' },
  completed: { icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-50 dark:bg-green-900/20', label: 'Hoàn thành' },
  failed: { icon: XCircle, color: 'text-red-600', bg: 'bg-red-50 dark:bg-red-900/20', label: 'Thất bại' },
}

export function DocumentUpload({
  documents,
  isLoading,
  onUpload,
  onDelete,
  isUploading,
  error
}: DocumentUploadProps) {
  const [isDragging, setIsDragging] = useState(false)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback(() => {
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      await uploadFile(files[0])
    }
  }, [])

  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      await uploadFile(file)
    }
    // Reset input
    e.target.value = ''
  }, [])

  const uploadFile = async (file: File) => {
    // Validate file type
    const allowedTypes = ['pdf', 'docx', 'doc', 'txt', 'png', 'jpg', 'jpeg', 'tiff']
    const ext = file.name.split('.').pop()?.toLowerCase() || ''

    if (!allowedTypes.includes(ext)) {
      alert(`Loại file không được hỗ trợ. Vui lòng tải lên: ${allowedTypes.join(', ')}`)
      return
    }

    // Validate file size (max 50MB)
    if (file.size > 50 * 1024 * 1024) {
      alert('Kích thước file không được vượt quá 50MB')
      return
    }

    try {
      await onUpload(file)
    } catch (err) {
      console.error('Upload failed:', err)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="flex flex-col h-full bg-background min-h-0">
      {/* Upload Zone */}
      <div className="p-4 border-b">
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={cn(
            'relative border-2 border-dashed rounded-xl p-6 text-center transition-colors',
            isDragging
              ? 'border-primary bg-primary/5'
              : 'border-border hover:border-primary/50 hover:bg-muted/50'
          )}
        >
          <input
            type="file"
            id="file-upload"
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            onChange={handleFileSelect}
            accept=".pdf,.docx,.doc,.txt,.png,.jpg,.jpeg,.tiff"
          />
          <Upload className={cn(
            'w-8 h-8 mx-auto mb-2',
            isDragging ? 'text-primary' : 'text-muted-foreground'
          )} />
          <p className="text-sm font-medium mb-1">
            {isDragging ? 'Thả file vào đây' : 'Kéo thả file vào đây'}
          </p>
          <p className="text-xs text-muted-foreground">
            hoặc click để chọn file (PDF, DOCX, TXT, PNG, JPG - tối đa 50MB)
          </p>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="px-4 py-2">
          <div className="bg-destructive/10 text-destructive text-xs px-3 py-2 rounded-lg">
            {error}
          </div>
        </div>
      )}

      {/* Documents List */}
      <div className="flex-1 overflow-y-auto p-4 custom-scrollbar min-h-0">
        {isLoading && documents.length === 0 ? (
          <div className="flex items-center justify-center min-h-full">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : documents.length === 0 ? (
          <div className="flex flex-col items-center justify-center min-h-full text-center py-8">
            <FileText className="w-12 h-12 text-muted-foreground/30 mb-3" />
            <p className="text-sm text-muted-foreground">
              Chưa có tài liệu nào. Tải lên tài liệu để bắt đầu.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {documents.map((doc) => {
              const Icon = FILE_ICONS[doc.file_type] || FILE_ICONS.default
              const status = STATUS_CONFIG[doc.status]
              const StatusIcon = status.icon
              const uploading = isUploading(doc.filename)

              return (
                <div
                  key={doc.id}
                  className={cn(
                    'flex items-center gap-3 p-3 rounded-lg border transition-all',
                    uploading ? 'bg-primary/5 border-primary/20' : 'bg-card hover:bg-muted/50'
                  )}
                >
                  {/* File Icon */}
                  <div className="shrink-0">
                    <Icon className="w-8 h-8 text-muted-foreground" />
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{doc.filename}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatFileSize(doc.file_size)}
                    </p>
                  </div>

                  {/* Status */}
                  <div className={cn(
                    'flex items-center gap-1.5 px-2 py-1 rounded-full text-xs',
                    status.bg,
                    status.color
                  )}>
                    <StatusIcon className={cn(
                      'w-3 h-3',
                      status.icon === Loader2 && 'animate-spin'
                    )} />
                    <span>{uploading ? 'Đang tải lên...' : status.label}</span>
                  </div>

                  {/* Delete */}
                  {!uploading && (
                    <button
                      onClick={() => onDelete(doc.id)}
                      className="shrink-0 p-1.5 rounded-md hover:bg-destructive/10 hover:text-destructive transition-colors"
                      title="Xoá tài liệu"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
