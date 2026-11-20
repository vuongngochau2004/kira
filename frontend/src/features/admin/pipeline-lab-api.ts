/** Typed client for the admin pipeline lab. */
import { z } from 'zod'

import { apiErrorMessage, ApiError, fetchAPI } from '@/lib/api/http'

const basePath = '/api/v1/admin/pipeline-lab'

export const extractionSchema = z.object({
  success: z.boolean(),
  text: z.string(),
  pages: z.number().optional(),
  page_texts: z.array(z.tuple([z.number(), z.string()])).optional(),
  confidence: z.number().optional(),
  metadata: z.record(z.string(), z.unknown()),
  error: z.string().nullable(),
  latency_ms: z.number(),
})

export const classificationSchema = z.object({
  intent: z.string(),
  confidence: z.number(),
  reason: z.string(),
  metadata: z.record(z.string(), z.unknown()),
  handler_hint: z.string().nullable().optional(),
  latency_ms: z.number(),
})

export const rerankingSchema = z.object({
  mode: z.string(),
  fallback: z.boolean(),
  raw_response: z.string().nullable().optional(),
  error: z.string().nullable().optional(),
  latency_ms: z.number(),
  results: z.array(z.object({
    id: z.string(),
    text: z.string(),
    rerank_score: z.number().optional(),
  }).passthrough()),
})

export type ExtractionResult = z.infer<typeof extractionSchema>
export type ClassificationResult = z.infer<typeof classificationSchema>
export type RerankingResult = z.infer<typeof rerankingSchema>

export async function demoExtraction(file: File): Promise<ExtractionResult> {
  const body = new FormData()
  body.append('file', file)
  const response = await fetch(`${basePath}/extract`, {
    method: 'POST',
    body,
    credentials: 'include',
  })
  const payload: unknown = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new ApiError(apiErrorMessage(payload, 'Extraction failed'), response.status)
  }
  return extractionSchema.parse(payload)
}

export async function demoClassification(query: string): Promise<ClassificationResult> {
  const payload = await fetchAPI<unknown>(`${basePath}/classify`, {
    method: 'POST',
    body: JSON.stringify({ query }),
  })
  return classificationSchema.parse(payload)
}

export async function demoReranking(
  query: string,
  documents: string[],
  topK: number,
): Promise<RerankingResult> {
  const payload = await fetchAPI<unknown>(`${basePath}/rerank`, {
    method: 'POST',
    body: JSON.stringify({ query, documents, top_k: topK }),
  })
  return rerankingSchema.parse(payload)
}
