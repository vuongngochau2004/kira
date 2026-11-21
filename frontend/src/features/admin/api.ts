/** Admin API: dashboard overview. */
import { fetchAPI } from '@/lib/api/http'
import type { Document } from '@/features/documents/api'

export interface AdminOverview {
  generated_at: string
  system: {
    status: 'ok' | 'degraded' | 'error' | string
    services: Array<{
      name: string
      status: 'ok' | 'configured' | 'missing' | 'error' | string
      detail?: string
    }>
  }
  documents: {
    total: number
    completed: number
    processing: number
    failed: number
    status_counts: Record<string, number>
    total_chunks: number
    recent: Document[]
    failed_items: Document[]
    deletion_jobs: {
      status_counts: Record<string, number>
      latest_error?: string | null
    }
  }
  retrieval: {
    avg_source_score: number | null
    citation_coverage: number | null
    avg_sources_per_answer: number | null
    answers_with_sources: number
    answers_sampled: number
    needs_review: number
  }
  answers: {
    avg_quality_score: number | null
    quality_gate_pass_rate: number | null
    low_quality_count: number
    recent_reviews: Array<{
      id: string
      conversation_id: string
      created_at: string
      reason: string
      source_count: number
      quality_score: number | null
      preview: string
    }>
  }
  activity: {
    total_conversations: number
    conversations_24h: number
    messages_24h: number
    assistant_messages_24h: number
  }
}

export const adminAPI = {
  overview: () => fetchAPI<AdminOverview>('/api/v1/admin/overview'),
}
