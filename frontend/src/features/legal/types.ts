/** Types shared by the legal admin screens and legal chat rendering. */

export type LegalDocumentStatus =
  | 'uploaded'
  | 'parsing'
  | 'in_review'
  | 'publishing'
  | 'published'
  | 'failed'

export type LegalDocType = 'law' | 'decree' | 'circular' | 'decision' | 'resolution' | 'other'

export interface LegalDocument {
  id: string
  number: string
  doc_type: LegalDocType
  title: string
  issuer: string
  issued_date: string
  effective_date: string
  source_url: string | null
  status: LegalDocumentStatus
  warnings: string[]
  error_detail: string | null
  provision_count: number
  published_at: string | null
  created_at: string | null
}

export type CandidateStatus = 'pending' | 'approved' | 'rejected' | 'unresolved_target'

export type RelationType = 'AMENDS' | 'REPEALS' | 'REPLACES' | 'GUIDES' | 'BASED_ON'

export interface RelationCandidate {
  id: string
  legal_document_id: string
  type: RelationType
  source_provision_key: string | null
  target_number: string
  target_provision_ref: string | null
  effective_date: string
  new_text: string | null
  evidence_text: string
  evidence_page: number | null
  extractor: string
  confidence: number
  status: CandidateStatus
  flags: string[]
  reviewed_by: string | null
  reviewed_at: string | null
  review_note: string | null
}

export interface CandidateReview {
  action: 'approve' | 'reject' | 'edit'
  note?: string
  target_number?: string
  target_provision_ref?: string
  effective_date?: string
  new_text?: string
}

export interface ReviewResult {
  candidate: RelationCandidate
  republish_task_id: string | null
}

export interface TaskAccepted {
  document_id: string
  task_id: string
}

export interface LegalUploadInput {
  file: File
  number: string
  doc_type: LegalDocType
  title: string
  issuer: string
  issued_date: string
  effective_date: string
  source_url?: string
}

export interface ProvisionVersion {
  version_id: string
  text: string
  page: number | null
  valid_from: string
  valid_to: string | null
}

export interface ProvisionHistory {
  provision_key: string
  label: string
  number: string
  title: string
  doc_type: string
  versions: ProvisionVersion[]
  in_force: ProvisionVersion | null
}

export type LegalSourceRole = 'primary' | 'guide' | 'before' | 'after' | 'removed' | 'added'

/** `legal` object on a chat citation. */
export interface LegalCitationInfo {
  number: string
  doc_type: string
  provision_key: string
  label: string
  title: string
  valid_from: string
  valid_to: string | null
  amended_after: string | null
  role: LegalSourceRole
}

/** `legal` object on an assistant message (SSE status/metadata, persisted metadata). */
export interface LegalAnswerInfo {
  mode: 'single' | 'compare'
  dates: string[]
  temporal_source?: string
  notices: string[]
}
