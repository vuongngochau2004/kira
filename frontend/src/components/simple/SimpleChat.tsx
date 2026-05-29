'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Loader2, X, Paperclip } from 'lucide-react'
import { ThinkingBlock } from '@/components/streaming/ThinkingBlock'
import { SourceCitation } from '@/components/streaming/SourceCitation'
import { SourcePanel } from '@/components/streaming/SourcePanel'
import { cn } from '@/lib/utils'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export interface ThinkingStep {
  node: string
  status: 'pending' | 'running' | 'complete'
  duration?: number
  timestamp?: number
}

export interface SourceChunk {
  id: string
  content: string
  score: number
  document_id?: string
  chunk_index?: number
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sources?: SourceChunk[]
  thinking?: ThinkingStep[]
}

interface SimpleChatProps {
  messages: Message[]
  isLoading: boolean
  onSendMessage: (content: string) => void
  onClearChat: () => void
  error?: string | null
  className?: string
}

export function SimpleChat({
  messages,
  isLoading,
  onSendMessage,
  onClearChat,
  error,
  className
}: SimpleChatProps) {
  const [input, setInput] = useState('')
  const [sourcePanelOpen, setSourcePanelOpen] = useState(false)
  const [selectedSources, setSelectedSources] = useState<SourceChunk[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isLoading) {
      bottomRef.current?.scrollIntoView({ behavior: 'auto' })
    } else {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, isLoading])

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    onSendMessage(input.trim())
    setInput('')

    setTimeout(() => textareaRef.current?.focus(), 100)
  }, [input, isLoading, onSendMessage])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }, [handleSubmit])

  const handleFileAttach = () => {
    fileInputRef.current?.click()
  }

  const isLastMessageLoading = (messageIndex: number) => {
    return isLoading && messageIndex === messages.length - 1
  }

  return (
    <div className={cn('flex flex-col h-full bg-background min-h-0', className)}>
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto min-h-0">
        <div className="max-w-3xl mx-auto px-4 py-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center min-h-full text-center py-12">
              <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
                <Send className="w-8 h-8 text-primary" />
              </div>
              <h3 className="text-xl font-semibold mb-2">K.I.R.A</h3>
              <p className="text-sm text-muted-foreground max-w-xs">
                Trợ lý AI nghiên cứu của bạn. Hãy đặt câu hỏi hoặc tải lên tài liệu để bắt đầu.
              </p>
            </div>
          ) : (
            <>
              {messages.map((message, index) => (
                <div
                  key={message.id}
                  className={cn(
                    'flex gap-3 mb-6',
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  )}
                >
                  {/* Message Content */}
                  <div className={cn(
                    'max-w-[85%]',
                    message.role === 'user' ? 'flex flex-col items-end' : 'flex flex-col w-full max-w-full'
                  )}>
                    {/* Thinking Block - for assistant messages */}
                    {message.role === 'assistant' && (
                      <ThinkingBlock
                        steps={message.thinking || []}
                        isLoading={isLastMessageLoading(index)}
                      />
                    )}

                    {/* Response Content */}
                    {message.role === 'assistant' ? (
                      <div className="text-base py-2 text-foreground">
                        {!message.content && isLastMessageLoading(index) ? (
                          <div className="flex items-center gap-2 text-muted-foreground">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span className="text-sm">Đang phản hồi...</span>
                          </div>
                        ) : (
                          <div className="prose dark:prose-invert max-w-none text-foreground text-[15px] md:text-base leading-relaxed break-words">
                            <ReactMarkdown 
                              remarkPlugins={[remarkGfm]}
                              components={{
                                p: ({ children }) => <p className="mb-4 last:mb-0 leading-relaxed">{children}</p>,
                                strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
                                ul: ({ children }) => <ul className="list-disc pl-5 mb-4 space-y-1">{children}</ul>,
                                ol: ({ children }) => <ol className="list-decimal pl-5 mb-4 space-y-1">{children}</ol>,
                                li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                                h1: ({ children }) => <h1 className="text-2xl font-bold mt-6 mb-3 text-foreground">{children}</h1>,
                                h2: ({ children }) => <h2 className="text-xl font-bold mt-5 mb-2.5 text-foreground">{children}</h2>,
                                h3: ({ children }) => <h3 className="text-lg font-semibold mt-4 mb-2 text-foreground">{children}</h3>,
                                a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">{children}</a>,
                                code: ({ className, children }) => {
                                  const match = /language-(\w+)/.exec(className || '')
                                  return match ? (
                                    <pre className="bg-muted p-4 rounded-xl overflow-x-auto text-sm my-4 font-mono">
                                      <code>{children}</code>
                                    </pre>
                                  ) : (
                                    <code className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono">{children}</code>
                                  )
                                }
                              }}
                            >
                              {message.content || ''}
                            </ReactMarkdown>
                          </div>
                        )}
                      </div>
                    ) : message.content ? (
                      /* User message */
                      <div className="bg-muted/60 text-foreground px-5 py-3 rounded-3xl">
                        <p className="whitespace-pre-wrap break-words leading-relaxed">
                          {message.content}
                        </p>
                      </div>
                    ) : null}

                    {/* Source Citation */}
                    {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                      <div className="mt-2">
                        <SourceCitation
                          sources={message.sources}
                          onClick={() => {
                            setSelectedSources(message.sources!)
                            setSourcePanelOpen(true)
                          }}
                        />
                      </div>
                    )}
                  </div>
                </div>
              ))}

              <div ref={bottomRef} />
            </>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="max-w-3xl mx-auto px-4 pb-2">
          <div className="bg-destructive/10 text-destructive text-sm px-4 py-3 rounded-xl flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => window.location.reload()} className="text-xs underline hover:underline">
              Thử lại
            </button>
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="shrink-0 border-t bg-background">
        <div className="max-w-3xl mx-auto p-4">
          <form onSubmit={handleSubmit} className="relative">
            <div className="flex items-end gap-2">
              {/* Attach Button */}
              <button
                type="button"
                onClick={handleFileAttach}
                className="shrink-0 h-10 w-10 rounded-full flex items-center justify-center text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                title="Đính kèm tài liệu"
              >
                <Paperclip className="w-5 h-5" />
              </button>
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".pdf,.docx,.doc,.txt,.png,.jpg,.jpeg,.tiff"
              />

              {/* Text Input */}
              <div className="flex-1 relative">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Nhập tin nhắn..."
                  rows={1}
                  className={cn(
                    'w-full resize-none rounded-full border border-input bg-background',
                    'px-4 py-2.5 pr-10 text-sm placeholder:text-muted-foreground',
                    'focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary',
                    'disabled:opacity-50 disabled:cursor-not-allowed',
                    'max-h-32 overflow-y-auto'
                  )}
                  disabled={isLoading}
                  style={{ minHeight: '42px' }}
                />
                {messages.length > 0 && input.length === 0 && (
                  <button
                    type="button"
                    onClick={onClearChat}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors p-1"
                    title="Xoá cuộc trò chuyện"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* Send Button */}
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className={cn(
                  'shrink-0 h-10 w-10 rounded-full flex items-center justify-center',
                  'bg-primary text-primary-foreground',
                  'hover:bg-primary/90 transition-colors',
                  'disabled:opacity-40 disabled:cursor-not-allowed'
                )}
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Source Panel */}
      <SourcePanel
        sources={selectedSources}
        isOpen={sourcePanelOpen}
        onClose={() => setSourcePanelOpen(false)}
      />
    </div>
  )
}
