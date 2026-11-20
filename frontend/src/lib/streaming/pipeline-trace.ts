/**
 * Pipeline trace: the ordered steps (intent classification + LangGraph nodes) that produced an
 * assistant answer. Built live from `routing`/`status` SSE chunks and restored from the
 * persisted `message.metadata.pipeline` when a conversation is reloaded.
 */

export interface PipelineStep {
  /** `classify`, a LangGraph node (`orchestrator`, `retrieval`, `generation`, `quality`) or a
   *  handler-specific stage such as the legal `temporal` step. */
  stage: string
  metadata: Record<string, unknown>
}

export type PipelineStepTone = 'success' | 'warning' | 'error'

export interface PipelineStepView {
  label: string
  detail: string | null
  tone: PipelineStepTone
  durationMs: number | null
  notes: string[]
  pending: boolean
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function asNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

/** Validate a persisted/streamed trace; returns undefined when there is nothing to show. */
export function toPipelineSteps(raw: unknown): PipelineStep[] | undefined {
  if (!Array.isArray(raw)) return undefined
  const steps = raw
    .filter(isRecord)
    .filter((step) => typeof step.stage === 'string' && step.stage.length > 0)
    .map((step) => ({
      stage: step.stage as string,
      metadata: isRecord(step.metadata) ? step.metadata : {},
    }))
  return steps.length > 0 ? steps : undefined
}

/** A trace is only worth rendering when a graph ran, not for classification alone. */
export function hasGraphSteps(steps: PipelineStep[] | undefined): steps is PipelineStep[] {
  return Boolean(steps?.some((step) => step.stage !== 'classify'))
}

export function formatDuration(ms: number): string {
  return ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(1)}s`
}

export function totalDurationMs(steps: PipelineStep[]): number {
  return steps.reduce((sum, step) => sum + (asNumber(step.metadata.duration_ms) ?? 0), 0)
}

const QUALITY_DECISION_TEXT: Record<string, string> = {
  pass: 'đạt',
  regenerate: 'chưa đạt → sinh lại',
  fallback: 'không đạt → dùng phương án dự phòng',
}

/** Map a raw step to the labels shown in the timeline. */
export function describePipelineStep(step: PipelineStep): PipelineStepView {
  const meta = step.metadata
  const iteration = asNumber(meta.iteration) ?? Math.max((asNumber(meta.attempt) ?? 1) - 1, 0)
  const pending = meta.state === 'started' || (
    step.stage === 'generation' && asNumber(meta.attempt) !== null &&
    asNumber(meta.duration_ms) === null
  )
  const view: PipelineStepView = {
    label: step.stage,
    detail: null,
    tone: 'success',
    durationMs: asNumber(meta.duration_ms),
    notes: [],
    pending,
  }

  switch (step.stage) {
    case 'classify': {
      const confidence = asNumber(meta.confidence)
      view.label = 'Phân loại ý định'
      view.detail = [meta.intent, confidence !== null ? confidence.toFixed(2) : null]
        .filter(Boolean)
        .join(' · ') || null
      break
    }
    case 'orchestrator':
      view.label = 'Điều phối (Orchestrator)'
      if (meta.fallback) {
        view.tone = 'error'
        view.detail = `dự phòng: ${String(meta.fallback_reason ?? 'không rõ')}`
      } else {
        view.detail = '→ truy xuất'
      }
      break
    case 'retrieval': {
      const docs = asNumber(meta.docs_retrieved) ?? 0
      const queries = Array.isArray(meta.refined_queries) ? meta.refined_queries : []
      view.label = 'Truy xuất tài liệu'
      view.detail = `${docs} tài liệu · ${queries.length} truy vấn`
      if (docs === 0) view.tone = 'warning'
      view.notes = queries.filter((query): query is string => typeof query === 'string')
      break
    }
    case 'generation': {
      const length = asNumber(meta.response_length)
      view.label = iteration > 0 ? `Sinh lại câu trả lời (lần ${iteration})` : 'Sinh câu trả lời'
      view.detail = length !== null ? `${length} ký tự` : null
      break
    }
    case 'quality': {
      const score = asNumber(meta.quality_score)
      const decision = typeof meta.decision === 'string' ? meta.decision : null
      view.label = 'Kiểm định chất lượng'
      view.detail = [
        score !== null ? `điểm ${score.toFixed(2)}` : null,
        decision ? QUALITY_DECISION_TEXT[decision] ?? decision : null,
      ]
        .filter(Boolean)
        .join(' · ') || null
      view.tone = decision === 'fallback' ? 'error' : decision === 'regenerate' ? 'warning' : 'success'
      view.notes = Array.isArray(meta.issues)
        ? meta.issues.filter((issue): issue is string => typeof issue === 'string')
        : []
      break
    }
    case 'temporal':
      view.label = 'Xác định thời điểm áp dụng'
      break
    default:
      break
  }

  if (pending) {
    view.detail = 'Đang xử lý…'
    view.tone = 'success'
    view.notes = []
  }

  return view
}
