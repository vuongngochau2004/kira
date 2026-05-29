export interface MockSource {
  id: string
  type: 'pdf' | 'docx' | 'web'
  title: string
  snippet: string
  page?: number
  score: number
}

export const MOCK_SOURCES: MockSource[] = [
  {
    id: '1',
    type: 'pdf',
    title: 'Introduction to Machine Learning.pdf',
    snippet: 'Machine learning is a subset of artificial intelligence that focuses on building systems that can learn from data...',
    page: 12,
    score: 0.95,
  },
  {
    id: '2',
    type: 'docx',
    title: 'AI Research Notes.docx',
    snippet: 'Neural networks are computing systems inspired by biological neural networks that constitute animal brains...',
    score: 0.87,
  },
  {
    id: '3',
    type: 'web',
    title: 'Wikipedia - Artificial Intelligence',
    snippet: 'Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to the natural intelligence displayed by animals and humans...',
    score: 0.72,
  },
]
