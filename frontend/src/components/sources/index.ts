/**
 * Source Panel Components Export
 * Centralized exports for source panel module
 */

// Main Component
export { SourcePanel } from './SourcePanel'

// Components
export { SourceCard } from './components/SourceCard'
export { SourceList } from './components/SourceList'
export { ChunkRenderer } from './components/ChunkRenderer'
export { SimplifiedChunkViewer } from './components/SimplifiedChunkViewer'
export { PanelResizer } from './components/PanelResizer'
export type { ResizerProps } from './components/PanelResizer'

// Hooks
export { useSourcePanelState } from './hooks/use-source-panel-state'
export { useDocumentData } from './hooks/use-document-data'
export { useTextMatching, cleanStringForMatching, findLongestMatch, getCleanSearchPhrase } from './hooks/use-text-matching'
export { useImprovedTextMatching, findRelevantSegment, normalizeText, calculateSimilarity } from './hooks/use-improved-text-matching'

// Types
export type {
  Source,
  SourceChunk,
  GroupedSource,
  DocumentChunk,
  DocumentData,
  SourcePanelUIState,
  SourceCardProps,
  SourcePanelAction,
  TextMatchResult,
  HighlightRenderProps,
  SupportedFileType,
} from './types/source-panel-types'

// State
export { sourcePanelReducer, createInitialSourcePanelState } from './state/source-panel-reducer'
export { documentDataReducer, createInitialDocumentDataState } from './state/source-panel-reducer'

// Constants
export { SOURCE_PANEL_CONSTANTS } from './types/source-panel-types'
