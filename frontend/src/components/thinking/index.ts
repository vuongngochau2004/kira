/**
 * Thinking hierarchy components for multi-agent reasoning display
 *
 * Exports the main ThinkingHierarchy component
 * for displaying structured thinking from multiple AI agents.
 */

export { ThinkingHierarchy } from './ThinkingHierarchy'

// Re-export types for convenience (excluding ThinkingHierarchy which is exported above)
export type {
  ExecutionThinking,
  ReasoningThinking,
} from '@/types/thinking'
