import Link from 'next/link'
import { ChevronRight } from 'lucide-react'
import { DOC_TYPE_LABELS, formatLegalDate } from '@/lib/legal/format'
import type { LegalDocument } from '@/lib/legal/types'
import { DocumentStatusBadge } from './LegalStatusBadge'

export function LegalDocumentTable({ documents }: { documents: LegalDocument[] }) {
  if (documents.length === 0) {
    return <p className="py-8 text-center text-sm text-muted-foreground">Chưa có văn bản pháp luật nào.</p>
  }
  return (
    <ul className="divide-y rounded-lg border">
      {documents.map((document) => (
        <li key={document.id}>
          <Link
            href={`/admin/legal/${document.id}`}
            className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-muted/40"
          >
            <div className="min-w-0 flex-1 space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-semibold">{document.number}</span>
                <span className="text-xs text-muted-foreground">{DOC_TYPE_LABELS[document.doc_type]}</span>
                <DocumentStatusBadge status={document.status} />
              </div>
              <p className="truncate text-sm">{document.title}</p>
              <div className="flex flex-wrap gap-x-3 text-xs text-muted-foreground">
                <span>Hiệu lực {formatLegalDate(document.effective_date)}</span>
                {document.provision_count > 0 && <span>{document.provision_count} điều khoản</span>}
                {document.warnings.length > 0 && (
                  <span className="text-amber-700 dark:text-amber-300">{document.warnings.length} cảnh báo</span>
                )}
              </div>
            </div>
            <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
          </Link>
        </li>
      ))}
    </ul>
  )
}
