'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth-store'
import {
  LogOut,
  ChevronLeft,
  Search,
  Upload,
  MessageSquarePlus,
  FileText,
  File,
  Trash2,
  Loader2,
  Eye,
  Download,
  FileImage,
  Presentation,
  ChevronDown,
  ChevronRight
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useDocumentsUpload } from '@/lib/hooks/use-documents-upload'
import { DocumentPreviewDialog } from '@/components/document-preview-dialog'
import { KiraLogoIcon } from '@/components/common/KiraLogo'
import { ThemeToggleDropdown } from '@/components/common/ThemeToggle'
import { documentsAPI } from '@/lib/api/simple-client'
import { cn } from '@/lib/utils'

export type SidebarPage = 'chat' | 'conversations' | 'uploads'

interface SidebarExpandedProps {
  page: SidebarPage
  onPageChange?: (page: SidebarPage) => void
  onToggle: () => void
  onCreateConversation?: () => void
  customContent?: React.ReactNode
}

// Beautiful, modern iOS-style colored icon configuration in sidebar
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

export function SidebarExpanded({
  page,
  onPageChange,
  onToggle,
  onCreateConversation,
  customContent,
}: SidebarExpandedProps) {
  const router = useRouter()
  const { user, logout } = useAuthStore()
  const [mounted, setMounted] = useState(false)

  // Collapsible list state
  const [isDocumentsExpanded, setIsDocumentsExpanded] = useState(true)

  // Document states inside sidebar
  const { documents, deleteDocument, isLoading } = useDocumentsUpload()
  const [previewDocId, setPreviewDocId] = useState<string | null>(null)
  const [previewFilename, setPreviewFilename] = useState<string>('')
  const [isPreviewOpen, setIsPreviewOpen] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  // Filter completed documents
  const completedDocs = documents.filter((doc) => doc.status === 'completed')

  return (
    <div className="flex flex-col h-full w-[280px] bg-background border-r">
      {/* Header with Logo and Toggle */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <KiraLogoIcon size={36} variant="gradient" />
            <div>
              <h1 className="text-sm font-bold">K.I.R.A</h1>
              <p className="text-[10px] text-muted-foreground">
                Knowledge & Intelligent Robotic Assistant
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={onToggle}
            aria-label="Thu gọn thanh bên"
            aria-expanded="true"
          >
            <ChevronLeft className="w-4 h-4" />
          </Button>
        </div>

        {/* Navigation Buttons - Vertical Stack */}
        <div className="space-y-2">
          {/* New Chat Button */}
          <Button
            variant={page === 'chat' ? 'default' : 'outline'}
            className="w-full justify-start"
            onClick={() => {
              onCreateConversation?.()
            }}
          >
            <MessageSquarePlus className="w-4 h-4 mr-2" />
            Cuộc trò chuyện mới
          </Button>

          {/* Search Button */}
          <Button
            variant={page === 'conversations' ? 'default' : 'outline'}
            className="w-full justify-start"
            onClick={() => {
              onPageChange?.('conversations')
              router.push('/conversations')
            }}
          >
            <Search className="w-4 h-4 mr-2" />
            Tìm kiếm cuộc trò chuyện
          </Button>

          {/* Documents Button */}
          <Button
            variant={page === 'uploads' ? 'default' : 'outline'}
            className="w-full justify-start"
            onClick={() => {
              onPageChange?.('uploads')
              router.push('/uploads')
            }}
          >
            <Upload className="w-4 h-4 mr-2" />
            Tài liệu
          </Button>
        </div>
      </div>

      {/* Dynamic Content - Collapsible Uploaded Documents List */}
      {customContent || (
        <div className="flex-1 overflow-hidden min-h-0 flex flex-col p-2 gap-1 bg-muted/5">
          {/* Collapsible Header Row */}
          <div 
            onClick={() => setIsDocumentsExpanded(!isDocumentsExpanded)}
            className="px-3 py-2 flex items-center justify-between shrink-0 cursor-pointer select-none rounded-lg hover:bg-muted/40 transition-colors text-muted-foreground hover:text-foreground"
          >
            <h2 className="text-[10px] font-bold uppercase tracking-wider">
              Tài liệu đã tải ({completedDocs.length})
            </h2>
            <div className="p-0.5 rounded-md shrink-0">
              {isDocumentsExpanded ? (
                <ChevronDown className="w-3.5 h-3.5" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5" />
              )}
            </div>
          </div>
          
          {/* Conditionally Render Document List based on Collapsible State */}
          {isDocumentsExpanded && (
            <div className="flex-1 flex flex-col min-h-0 transition-all duration-300">
              {isLoading && completedDocs.length === 0 ? (
                <div className="flex items-center justify-center p-4">
                  <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                </div>
              ) : completedDocs.length === 0 ? (
                <div className="flex items-center justify-center p-4 text-center">
                  <p className="text-xs text-muted-foreground max-w-[200px] leading-relaxed">
                    Chưa có tài liệu nào.
                  </p>
                </div>
              ) : (
                <div className="flex-1 overflow-y-auto space-y-0.5 px-1 pr-1.5 scrollbar-thin">
                  {completedDocs.map((doc) => {
                    const fileType = FILE_TYPES[doc.file_type.toLowerCase()] || FILE_TYPES.default
                    const Icon = fileType.icon
                    const ext = doc.file_type.toLowerCase()
                    const isWordOrPpt = ext === 'doc' || ext === 'docx' || ext === 'ppt' || ext === 'pptx'

                    return (
                      <div
                        key={doc.id}
                        onClick={() => {
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
                        }}
                        className={cn(
                          'flex items-center gap-2 p-1.5 rounded-lg border border-transparent transition-all select-none group',
                          'hover:bg-muted/70 cursor-pointer hover:border-border/30'
                        )}
                      >
                        {/* Compact Icon */}
                        <div className={cn(
                          "w-7 h-7 rounded-md flex items-center justify-center shrink-0 border transition-transform duration-200 group-hover:scale-105",
                          fileType.bgColor
                        )}>
                          <Icon className={cn('w-4 h-4', fileType.color)} />
                        </div>

                        {/* Compact Truncated Name */}
                        <div className="flex-1 min-w-0">
                          <p className="text-[11px] font-medium truncate text-foreground group-hover:text-primary transition-colors">
                            {doc.filename}
                          </p>
                        </div>

                        {/* Inline Hover Action Helper & Trash */}
                        <div className="shrink-0 flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                          {isWordOrPpt ? (
                            <Download className="w-3.5 h-3.5 text-muted-foreground hover:text-foreground" />
                          ) : (
                            <Eye className="w-3.5 h-3.5 text-muted-foreground hover:text-foreground" />
                          )}
                          
                          <button
                            className="p-0.5 rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all shrink-0"
                            onClick={(e) => {
                              e.stopPropagation()
                              if (confirm(`Bạn có chắc chắn muốn xóa tài liệu "${doc.filename}"?`)) {
                                deleteDocument(doc.id)
                              }
                            }}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* User Footer */}
      {mounted && user && (
        <div className="p-4 border-t bg-zinc-900/10 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center font-bold text-xs text-zinc-300 shrink-0">
              {user.full_name ? user.full_name.charAt(0).toUpperCase() : user.email.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-zinc-200 truncate leading-none mb-1">
                {user.full_name || 'Người dùng'}
              </p>
              <p className="text-[10px] text-zinc-500 truncate leading-none">
                {user.email}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <ThemeToggleDropdown />
            <button
              onClick={() => logout()}
              className="p-1.5 rounded-lg text-zinc-500 hover:text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer shrink-0"
              title="Đăng xuất"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Preview Dialog inside Sidebar to enable preview on any page */}
      <DocumentPreviewDialog
        documentId={previewDocId}
        filename={previewFilename}
        isOpen={isPreviewOpen}
        onClose={() => setIsPreviewOpen(false)}
      />
    </div>
  )
}
