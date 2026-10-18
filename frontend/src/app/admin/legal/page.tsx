'use client'

import { RefreshCw } from 'lucide-react'
import { LegalAdminShell } from '@/components/legal/admin/LegalAdminShell'
import { LegalDocumentTable } from '@/components/legal/admin/LegalDocumentTable'
import { LegalUploadForm } from '@/components/legal/admin/LegalUploadForm'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useLegalDocuments } from '@/lib/legal/use-legal-documents'

export default function LegalCorpusPage() {
  const { documents, isLoading, error, reload } = useLegalDocuments()

  return (
    <LegalAdminShell
      title="Kho văn bản pháp luật"
      description="Tải lên, duyệt quan hệ và xuất bản văn bản dùng chung"
      backHref="/admin"
      actions={
        <Button variant="outline" size="sm" onClick={() => void reload()}>
          <RefreshCw className="h-4 w-4" />
          Làm mới
        </Button>
      }
    >
      <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Tải lên văn bản</CardTitle>
            <CardDescription>Nhập đúng số hiệu và ngày hiệu lực như trên văn bản gốc.</CardDescription>
          </CardHeader>
          <CardContent>
            <LegalUploadForm onUploaded={() => void reload()} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Văn bản ({documents.length})</CardTitle>
            <CardDescription>Danh sách tự cập nhật khi có văn bản đang được xử lý.</CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <div className="mb-3 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            )}
            {isLoading ? (
              <p className="py-8 text-center text-sm text-muted-foreground">Đang tải…</p>
            ) : (
              <LegalDocumentTable documents={documents} />
            )}
          </CardContent>
        </Card>
      </div>
    </LegalAdminShell>
  )
}
