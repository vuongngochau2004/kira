'use client'

import { useCallback, useState, useEffect } from 'react'
import { Upload, FileText, Trash2, Loader2, File, CheckCircle, XCircle, Clock, MoreVertical, Plus } from 'lucide-react'
import { Document } from '@/lib/api/simple-client'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'

interface DocumentPanelProps {
  documents: Document[]
  isLoading: boolean
  onUpload: (file: File) => Promise<Document | void>
  onDelete: (id: string) => Promise<void>
  isUploading: (filename: string) => boolean
  error?: string | null
  uploadDurations?: Record<string, number>
  activeUploadStarts?: Record<string, number>
  documentStarts?: Record<string, number>
}

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

export function DocumentPanel({
  documents,
  isLoading,
  onUpload,
  onDelete,
  isUploading,
  error,
  uploadDurations = {},
  activeUploadStarts = {},
  documentStarts = {}
}: DocumentPanelProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [showUploadZone, setShowUploadZone] = useState(false)
  const [now, setNow] = useState<number>(Date.now())

  useEffect(() => {
    const timer = setInterval(() => {
      setNow(Date.now())
    }, 1000)
    return () => clearInterval(timer)
  }, [])

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
    setShowUploadZone(false)

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
    <div className="hidden xl:flex xl:w-[360px] flex-col border-l bg-background h-full min-h-0">
      {/* Header */}
      <div className="h-14 border-b flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold">Tài liệu</h2>
          {documents.length > 0 && (
            <span className="text-xs text-muted-foreground">
              {documents.length} tài liệu
            </span>
          )}
        </div>
        <Button
          size="sm"
          variant="ghost"
          className="h-8 px-2 gap-1 text-xs"
          onClick={() => setShowUploadZone(!showUploadZone)}
        >
          <Plus className="w-4 h-4" />
          Tải lên
        </Button>
      </div>

      {/* Upload Zone - Collapsible */}
      {showUploadZone && (
        <div className="p-4 border-b">
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={cn(
              'relative border-2 border-dashed rounded-xl p-6 text-center transition-all',
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
            <Upload className={cn(
              'w-6 h-6 mx-auto mb-2',
              isDragging ? 'text-primary' : 'text-muted-foreground'
            )} />
            <p className="text-xs font-medium text-muted-foreground">
              {isDragging ? 'Thả file vào đây' : 'Kéo thả hoặc click để chọn file'}
            </p>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="px-4 py-2">
          <div className="bg-destructive/10 text-destructive text-xs px-3 py-2 rounded-lg">
            {error}
          </div>
        </div>
      )}

      {/* Documents List */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {isLoading && documents.length === 0 ? (
          <div className="flex items-center justify-center min-h-full">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        ) : documents.length === 0 ? (
          <div className="flex flex-col items-center justify-center min-h-full text-center p-6">
            <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-3">
              <FileText className="w-6 h-6 text-muted-foreground" />
            </div>
            <p className="text-sm text-muted-foreground">
              Chưa có tài liệu nào
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Tải lên tài liệu để bắt đầu trò chuyện
            </p>
          </div>
        ) : (
          <div className="divide-y">
            {documents.map((doc) => {
              const fileType = FILE_TYPES[doc.file_type] || FILE_TYPES.default
              const Icon = fileType.icon
              const uploading = isUploading(doc.filename)
              const isCurrentlyUploading = uploading || doc.status === 'uploading'
              const uploadDuration = uploadDurations[doc.id] || uploadDurations[doc.filename]

              return (
                <div
                  key={doc.id}
                  className={cn(
                    'flex items-center gap-3 px-4 py-3 hover:bg-muted/50 transition-colors',
                    isCurrentlyUploading && 'bg-primary/5'
                  )}
                >
                  {/* File Icon */}
                  <div className="shrink-0">
                    <Icon className={cn('w-8 h-8', fileType.color)} />
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{doc.filename}</p>
                    <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1.5 flex-wrap">
                      <span>{formatFileSize(doc.file_size)}</span>
                      {isCurrentlyUploading ? (
                        <span className="text-blue-500 font-medium flex items-center gap-1">
                          <Loader2 className="w-2.5 h-2.5 animate-spin" />
                          {(() => {
                            const startTime = activeUploadStarts[doc.filename]
                            return startTime ? `${Math.max(0, (now - startTime) / 1000).toFixed(0)}s` : 'Tải...'
                          })()}
                        </span>
                      ) : doc.status === 'processing' ? (
                        <span className="text-amber-500 font-medium flex items-center gap-1">
                          <Loader2 className="w-2.5 h-2.5 animate-spin" />
                          Đang xử lý {(() => {
                            const startTime = documentStarts[doc.id] || (doc.created_at ? (doc.created_at.endsWith('Z') ? Date.parse(doc.created_at) : Date.parse(doc.created_at + 'Z')) : null)
                            return startTime ? `(${Math.max(0, (now - startTime) / 1000).toFixed(0)}s)` : ''
                          })()}
                        </span>
                      ) : null}

                      {uploadDuration !== undefined && !isCurrentlyUploading && (
                        <>
                          <span className="text-[10px] opacity-40">•</span>
                          <span>Tải: {uploadDuration.toFixed(1)}s</span>
                        </>
                      )}
                    </p>
                  </div>

                  {/* Actions */}
                  {!isCurrentlyUploading && doc.status !== 'processing' && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <button
                          className="shrink-0 p-1.5 rounded-md hover:bg-muted transition-colors"
                          title="Thêm tùy chọn"
                        >
                          <MoreVertical className="w-4 h-4 text-muted-foreground" />
                        </button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={() => onDelete(doc.id)}
                          className="text-destructive focus:text-destructive"
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          Xoá tài liệu
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}

                  {(isCurrentlyUploading || doc.status === 'processing') && (
                    <Loader2 className="w-4 h-4 animate-spin text-muted-foreground shrink-0" />
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
