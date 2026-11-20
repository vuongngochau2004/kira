'use client'

import { useState, type FormEvent } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft, Loader2 } from 'lucide-react'

import { AuthGuard } from '@/components/auth/auth-guard'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import {
  demoClassification,
  demoExtraction,
  demoReranking,
  type ClassificationResult,
  type ExtractionResult,
  type RerankingResult,
} from '@/lib/api/pipeline-lab'
import { useAuthStore } from '@/lib/stores/auth-store'

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Không thể chạy phép thử'
}

function Detail({ value }: { value: unknown }): React.JSX.Element {
  return (
    <pre className="max-h-72 overflow-auto rounded-md border bg-muted/40 p-3 text-xs whitespace-pre-wrap break-all">
      {JSON.stringify(value, null, 2)}
    </pre>
  )
}

function ExtractionDemo(): React.JSX.Element {
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<ExtractionResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [running, setRunning] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    if (!file) return
    setRunning(true)
    setError(null)
    setResult(null)
    try {
      setResult(await demoExtraction(file))
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setRunning(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>OCR và trích xuất</CardTitle>
        <CardDescription>Ảnh chạy PaddleOCR; PDF chạy chiến lược trích xuất đang cấu hình, gồm OCR fallback khi cần. File chỉ dùng cho phép thử này.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
          <div className="min-w-64 flex-1 space-y-1">
            <label htmlFor="lab-file" className="text-sm font-medium">PDF, PNG hoặc JPEG (tối đa 10 MiB)</label>
            <Input id="lab-file" type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
          </div>
          <Button disabled={!file || running} type="submit">{running && <Loader2 className="animate-spin" />} Chạy trích xuất</Button>
        </form>
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
        {result && (
          <div className="space-y-3">
            <p className="text-sm">{result.success ? 'Thành công' : 'Thất bại'} · {result.latency_ms} ms {result.pages ? `· ${result.pages} trang` : ''} {result.confidence !== undefined ? `· confidence ${result.confidence.toFixed(3)}` : ''}</p>
            {result.error && <p role="alert" className="text-sm text-destructive">{result.error}</p>}
            <div>
              <p className="mb-1 text-sm font-medium">Văn bản đầu ra</p>
              <pre className="max-h-[32rem] overflow-auto rounded-md border bg-muted/40 p-4 text-sm whitespace-pre-wrap">{result.text || '(Không có văn bản)'}</pre>
            </div>
            <details><summary className="cursor-pointer text-sm">Metadata và raw response</summary><Detail value={{ metadata: result.metadata, page_texts: result.page_texts }} /></details>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function ClassifierDemo(): React.JSX.Element {
  const [query, setQuery] = useState('')
  const [expected, setExpected] = useState('unlabeled')
  const [result, setResult] = useState<ClassificationResult | null>(null)
  const [samples, setSamples] = useState<Array<{ query: string; expected: string; result: ClassificationResult }>>([])
  const [error, setError] = useState<string | null>(null)
  const [running, setRunning] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    setRunning(true)
    setError(null)
    setResult(null)
    try {
      const classified = await demoClassification(query.trim())
      setResult(classified)
      setSamples((current) => [...current, { query: query.trim(), expected, result: classified }])
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setRunning(false)
    }
  }

  const labeled = samples.filter((sample) => sample.expected !== 'unlabeled')
  const correct = labeled.filter((sample) => sample.expected === sample.result.intent).length

  return (
    <Card>
      <CardHeader><CardTitle>Classifier</CardTitle><CardDescription>Thử câu hỏi với cùng strategy chain mà chat sử dụng. Kết quả gồm intent, confidence, lý do và metadata.</CardDescription></CardHeader>
      <CardContent className="space-y-4">
        <form onSubmit={submit} className="space-y-3">
          <label htmlFor="lab-query" className="text-sm font-medium">Câu hỏi cần phân loại</label>
          <Textarea id="lab-query" value={query} maxLength={2000} onChange={(event) => setQuery(event.target.value)} placeholder="Ví dụ: Tóm tắt tài liệu tôi vừa tải lên" />
          <div className="space-y-1"><p className="text-sm font-medium">Intent mong đợi (tuỳ chọn)</p><Select value={expected} onValueChange={setExpected}><SelectTrigger aria-label="Intent mong đợi"><SelectValue /></SelectTrigger><SelectContent>{['unlabeled', 'rag', 'conversational', 'drafting', 'legal_qa', 'semantic', 'unknown'].map((intent) => <SelectItem key={intent} value={intent}>{intent === 'unlabeled' ? 'Chưa gán nhãn' : intent}</SelectItem>)}</SelectContent></Select></div>
          <Button type="submit" disabled={!query.trim() || running}>{running && <Loader2 className="animate-spin" />} Chạy classifier</Button>
        </form>
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
        {result && <div className="space-y-2"><p className="text-sm"><strong>{result.intent}</strong> · confidence {result.confidence.toFixed(3)} · {result.latency_ms} ms</p><p className="text-sm">{result.reason}</p><Detail value={result.metadata} /></div>}
        {samples.length > 0 && <div className="space-y-2 border-t pt-4"><div className="flex items-center justify-between"><p className="text-sm font-medium">Lịch sử phiên thử ({samples.length}){labeled.length > 0 && ` · đúng ${correct}/${labeled.length}`}</p><Button type="button" variant="ghost" size="sm" onClick={() => setSamples([])}>Xoá lịch sử</Button></div><div className="max-h-60 overflow-auto space-y-1">{samples.map((sample, index) => <p className="text-sm" key={index}><span className="text-muted-foreground">{index + 1}.</span> {sample.query} → <strong>{sample.result.intent}</strong>{sample.expected !== 'unlabeled' && ` (mong đợi: ${sample.expected})`}</p>)}</div></div>}
      </CardContent>
    </Card>
  )
}

function RerankerDemo(): React.JSX.Element {
  const [query, setQuery] = useState('')
  const [documents, setDocuments] = useState('')
  const [topK, setTopK] = useState(5)
  const [result, setResult] = useState<RerankingResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const candidates = documents.split(/\n\s*---\s*\n/).map((item) => item.trim()).filter(Boolean)

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    setRunning(true)
    setError(null)
    setResult(null)
    try {
      setResult(await demoReranking(query.trim(), candidates, topK))
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setRunning(false)
    }
  }

  return (
    <Card>
      <CardHeader><CardTitle>Reranker</CardTitle><CardDescription>Dán các đoạn ứng viên, ngăn bằng một dòng “---”. Xem thứ tự sau rerank và điểm TEI nếu cấu hình dùng TEI.</CardDescription></CardHeader>
      <CardContent className="space-y-4">
        <form onSubmit={submit} className="space-y-3">
          <label htmlFor="rerank-query" className="text-sm font-medium">Truy vấn</label>
          <Input id="rerank-query" value={query} maxLength={2000} onChange={(event) => setQuery(event.target.value)} />
          <label htmlFor="rerank-documents" className="text-sm font-medium">Các đoạn văn (2–20 đoạn)</label>
          <Textarea id="rerank-documents" className="min-h-44" value={documents} onChange={(event) => setDocuments(event.target.value)} placeholder={'Đoạn 1\n---\nĐoạn 2'} />
          <div className="flex items-end gap-3"><div className="space-y-1"><label htmlFor="rerank-top-k" className="text-sm font-medium">Top K</label><Input id="rerank-top-k" type="number" min={1} max={20} value={topK} onChange={(event) => setTopK(Number(event.target.value))} className="w-24" /></div><Button type="submit" disabled={!query.trim() || candidates.length < 2 || candidates.length > 20 || running}>{running && <Loader2 className="animate-spin" />} Chạy reranker</Button></div>
        </form>
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
        {result && <div className="space-y-3"><p className="text-sm">Chế độ {result.mode} · {result.latency_ms} ms {result.fallback && '· Rerank lỗi hoặc không trả điểm; giữ thứ tự đầu vào'}</p>{result.error && <p role="alert" className="text-sm text-destructive">{result.error}</p>}{result.raw_response && <details><summary className="cursor-pointer text-sm">Raw LLM response</summary><Detail value={result.raw_response} /></details>}{result.results.map((item, index) => <div className="rounded-md border p-3" key={`${item.id}-${index}`}><p className="mb-1 text-xs text-muted-foreground">#{index + 1} · đoạn gốc {item.id}{item.rerank_score !== undefined && ` · score ${item.rerank_score.toFixed(4)}`}</p><p className="whitespace-pre-wrap text-sm">{item.text}</p></div>)}</div>}
      </CardContent>
    </Card>
  )
}

export default function PipelineLabPage(): React.JSX.Element {
  const router = useRouter()
  const { user } = useAuthStore()
  return (
    <AuthGuard>
      <main className="mx-auto max-w-5xl space-y-6 px-4 py-8">
        <div className="flex items-center gap-3"><Button variant="ghost" size="icon" onClick={() => router.push('/admin')} aria-label="Quay lại admin"><ArrowLeft /></Button><div><h1 className="text-2xl font-semibold">Pipeline Lab</h1><p className="text-sm text-muted-foreground">Chạy độc lập từng bước để kiểm tra đầu ra và debug.</p></div></div>
        {user?.role !== 'admin' ? <p role="alert">Chỉ quản trị viên có thể dùng công cụ này.</p> : (
          <Tabs defaultValue="extract"><TabsList><TabsTrigger value="extract">OCR</TabsTrigger><TabsTrigger value="classify">Classifier</TabsTrigger><TabsTrigger value="rerank">Reranker</TabsTrigger></TabsList><TabsContent value="extract"><ExtractionDemo /></TabsContent><TabsContent value="classify"><ClassifierDemo /></TabsContent><TabsContent value="rerank"><RerankerDemo /></TabsContent></Tabs>
        )}
      </main>
    </AuthGuard>
  )
}
