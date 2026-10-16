import type {
  CandidateStatus,
  LegalAnswerInfo,
  LegalDocType,
  LegalDocumentStatus,
  LegalSourceRole,
  RelationType,
} from './types'

const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/

/** 'YYYY-MM-DD' → 'dd/mm/yyyy' by string manipulation (date-only values must not shift). */
export function formatLegalDate(value: string | null | undefined): string {
  if (!value) return ''
  const match = ISO_DATE.exec(value.slice(0, 10))
  if (!match) return value
  return `${match[3]}/${match[2]}/${match[1]}`
}

export function validityLabel(validFrom: string, validTo: string | null): string {
  return `Hiệu lực ${formatLegalDate(validFrom)} → ${validTo ? formatLegalDate(validTo) : 'nay'}`
}

/** In force on `day` iff validFrom <= day < validTo (ISO strings compare lexicographically). */
export function isInForceOn(validFrom: string, validTo: string | null, day: string): boolean {
  return validFrom <= day && (validTo === null || day < validTo)
}

export function todayIso(now: Date = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

export function appliedDateLabel(info: LegalAnswerInfo): string {
  if (info.mode === 'compare' && info.dates.length === 2) {
    return `So sánh quy định ngày ${formatLegalDate(info.dates[0])} và ngày ${formatLegalDate(info.dates[1])}`
  }
  return `Áp dụng tại ngày ${formatLegalDate(info.dates[0])}`
}

/** Validate an unknown `legal` payload from SSE or persisted message metadata. */
export function toLegalAnswerInfo(value: unknown): LegalAnswerInfo | undefined {
  if (!value || typeof value !== 'object') return undefined
  const raw = value as Record<string, unknown>
  if (raw.mode !== 'single' && raw.mode !== 'compare') return undefined
  if (!Array.isArray(raw.dates) || raw.dates.length === 0) return undefined
  return {
    mode: raw.mode,
    dates: raw.dates.map(String),
    temporal_source: typeof raw.temporal_source === 'string' ? raw.temporal_source : undefined,
    notices: Array.isArray(raw.notices) ? raw.notices.map(String) : [],
  }
}

export const DOC_TYPE_LABELS: Record<LegalDocType, string> = {
  law: 'Luật',
  decree: 'Nghị định',
  circular: 'Thông tư',
  decision: 'Quyết định',
  resolution: 'Nghị quyết',
  other: 'Văn bản khác',
}

export const DOCUMENT_STATUS_LABELS: Record<LegalDocumentStatus, string> = {
  uploaded: 'Đã tải lên',
  parsing: 'Đang phân tích',
  in_review: 'Chờ duyệt',
  publishing: 'Đang xuất bản',
  published: 'Đã xuất bản',
  failed: 'Lỗi',
}

export const CANDIDATE_STATUS_LABELS: Record<CandidateStatus, string> = {
  pending: 'Chờ duyệt',
  approved: 'Đã duyệt',
  rejected: 'Đã từ chối',
  unresolved_target: 'Chưa có văn bản đích',
}

export const RELATION_TYPE_LABELS: Record<RelationType, string> = {
  AMENDS: 'Sửa đổi, bổ sung',
  REPEALS: 'Bãi bỏ',
  REPLACES: 'Thay thế',
  GUIDES: 'Hướng dẫn thi hành',
  BASED_ON: 'Căn cứ',
}

export const ROLE_LABELS: Record<LegalSourceRole, string> = {
  primary: 'Quy định áp dụng',
  guide: 'Văn bản hướng dẫn',
  before: 'Trước thay đổi',
  after: 'Sau thay đổi',
  removed: 'Đã hết hiệu lực',
  added: 'Quy định mới',
}

/** Statuses that a background task will still change; screens poll while any is shown. */
export const ACTIVE_DOCUMENT_STATUSES: LegalDocumentStatus[] = ['uploaded', 'parsing', 'publishing']
