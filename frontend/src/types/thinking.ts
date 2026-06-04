/**
 * Thinking hierarchy types for multi-agent reasoning display
 * Separates system decisions, tool execution, and LLM reasoning into distinct layers
 */

/**
 * Layer 1: System routing decisions
 * From: OrchestratorAgent → RouterRegistry.route_stream()
 */
export interface RoutingThinking {
  router: string              // "RAGRouter" | "ConversationalRouter"
  intent?: string             // "rag" | "conversational"
  confidence?: number         // 0.0 - 1.0
  method?: string             // "quick_filter" | "semantic" | "llm_classification"
  timestamp: number
}

/**
 * Layer 2: Tool execution stages
 * From: RAGRouter → AgenticRAG.query_stream()
 */
export interface ExecutionThinking {
  stage: 'retrieval' | 'embedding' | 'search'
  iteration: number
  strategy: 'dense' | 'hybrid'
  docsRetrieved: number
  duration?: number           // milliseconds
  timestamp: number
}

/**
 * Layer 3: LLM cognitive reasoning
 * From: LLM Provider (GLM-4.5, Claude) response <thinking> tags
 */
export interface ReasoningThinking {
  content: string              // thinking text content
  provider?: string            // "GLM-4.5" | "Claude" | etc.
  isStreaming: boolean
  timestamp: number
}

/**
 * Complete thinking hierarchy structure
 * Combines all three layers with overall status
 */
export interface ThinkingHierarchy {
  routing?: RoutingThinking
  execution: ExecutionThinking[]
  reasoning?: ReasoningThinking
  status: 'pending' | 'running' | 'complete' | 'error'
  error?: string
}

/**
 * Legacy ThinkingStep for backward compatibility
 * @deprecated Use ThinkingHierarchy instead
 */
export interface ThinkingStep {
  node: string
  status: 'pending' | 'running' | 'complete'
  duration?: number
  timestamp?: number
}
