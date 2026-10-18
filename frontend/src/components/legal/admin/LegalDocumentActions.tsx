'use client'

import { RefreshCcw, Send, Trash2 } from 'lucide-react'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import type { LegalDocument } from '@/lib/legal/types'

export function documentActionState(document: LegalDocument) {
  const status = document.status
  return {
    canPublish: ['in_review', 'published', 'failed'].includes(status) && document.provision_count > 0,
    canReprocess: status === 'uploaded' || status === 'failed',
    canDelete: document.published_at === null && status !== 'parsing' && status !== 'publishing',
  }
}

interface LegalDocumentActionsProps {
  document: LegalDocument
  busy: boolean
  onPublish: () => void
  onReprocess: () => void
  onDelete: () => void
}

export function LegalDocumentActions({ document, busy, onPublish, onReprocess, onDelete }: LegalDocumentActionsProps) {
  const { canPublish, canReprocess, canDelete } = documentActionState(document)
  return (
    <div className="flex flex-wrap gap-2">
      <Button size="sm" onClick={onPublish} disabled={busy || !canPublish}>
        <Send className="h-4 w-4" />
        {document.published_at ? 'Xuất bản lại' : 'Xuất bản'}
      </Button>
      <Button size="sm" variant="outline" onClick={onReprocess} disabled={busy || !canReprocess}>
        <RefreshCcw className="h-4 w-4" />
        Phân tích lại
      </Button>
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button size="sm" variant="destructive" disabled={busy || !canDelete}>
            <Trash2 className="h-4 w-4" />
            Xóa
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Xóa văn bản {document.number}?</AlertDialogTitle>
            <AlertDialogDescription>
              Tệp gốc và các quan hệ đề xuất sẽ bị xóa. Quan hệ của văn bản khác trỏ tới văn bản này sẽ trở về trạng thái
              “Chưa có văn bản đích”.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Hủy</AlertDialogCancel>
            <AlertDialogAction onClick={onDelete}>Xóa</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
