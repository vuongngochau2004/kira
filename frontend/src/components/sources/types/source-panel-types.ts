/**
 * Source Panel Types and Interfaces
 * Defines all data structures for the source panel component system
 */

// ============================================
// Core Source Data Types
// ============================================

export interface SourceChunk {
  id: string;
  snippet: string;
  page?: number;
  score: number;
}

export interface Source {
  id: string;
  document_id: string | null;
  title: string;
  type: SupportedFileType;
  snippet: string;
  page?: number;
  score: number;
}

// ============================================
// Grouped Source Types
// ============================================

export interface GroupedSource {
  document_id: string | null;
  title: string;
  type: SupportedFileType;
  maxScore: number;
  chunks: SourceChunk[];
}

// ============================================
// Document Chunk Types
// ============================================

export interface DocumentChunk {
  id: string;
  chunk_index: number;
  content: string;
  metadata?: {
    page_number?: number;
    page?: number;
    [key: string]: unknown;
  };
}

export interface DocumentData {
  document_id: string;
  chunks: DocumentChunk[];
  loading: boolean;
  error: string | null;
}

// ============================================
// UI State Types
// ============================================

export type SupportedFileType = "pdf" | "docx" | "web";

export interface SourcePanelUIState {
  expandedDocument: string | null;
  selectedChunk: string | null;
  clipboard: {
    id: string | null;
    timestamp: number;
  };
}

export interface SourceCardProps {
  group: GroupedSource;
  index: number;
  isSelected: boolean;
  onExpand: (key: string) => void;
  onPreview: (documentId: string, filename: string) => void;
}

export interface DocumentPreviewerProps {
  document: GroupedSource;
  documentData: DocumentData | null;
  isLoading: boolean;
  activeChunk: SourceChunk | null;
  onChunkSelect: (chunkId: string) => void;
  onCopy: (id: string, text: string) => Promise<boolean>;
  copiedId: string | null;
}

// ============================================
// Helper Types
// ============================================

export type FileIconType = SupportedFileType;

export const FILE_ICONS: Record<FileIconType, string> = {
  pdf: "FileText",
  docx: "FileText",
  web: "Globe",
} as const;

// ============================================
// Match Result Types
// ============================================

export interface TextMatchResult {
  index: number;
  length: number;
  matchedText: string;
}

export interface HighlightRenderProps {
  content: string;
  snippets: string[];
  isSelected: boolean;
  onChunkClick?: (chunkId: string) => void;
  chunkId?: string;
}

// ============================================
// Action Types for State Management
// ============================================

export type SourcePanelAction =
  | { type: "EXPAND_DOCUMENT"; payload: string | null }
  | { type: "SELECT_CHUNK"; payload: string | null }
  | { type: "COPY_TO_CLIPBOARD"; payload: { id: string; timestamp: number } }
  | { type: "LOAD_DOCUMENT_START"; payload: string }
  | {
      type: "LOAD_DOCUMENT_SUCCESS";
      payload: { id: string; data: DocumentChunk[] };
    }
  | { type: "LOAD_DOCUMENT_ERROR"; payload: { id: string; error: string } };

// ============================================
// Constants
// ============================================

export const SOURCE_PANEL_CONSTANTS = {
  WIDTHS: {
    COLLAPSED: 0,
    LIST_ONLY: 340,
    SOURCE_ONLY: 440,
    SOURCE_ONLY_MIN: 360,
    SOURCE_ONLY_MAX: 640,
    SPLIT_VIEW_LEFT: 340,
    SPLIT_VIEW_LEFT_MAX: 600,
    SPLIT_VIEW_RIGHT: 560,
    SPLIT_VIEW_MIN: 680,
    SPLIT_VIEW_MAX: 1120,
    TOTAL_SPLIT: 900,
    MAX_WIDTH: "95vw",
  },
  ANIMATION: {
    DURATION: 300,
    EASING: "ease-in-out",
  },
  SCROLL: {
    AUTO_SCROLL_DELAY: 300,
    HIGHLIGHT_SCROLL_DELAY: 200,
  },
  CLIPBOARD: {
    RESET_DELAY: 2000,
  },
  TRUNCATE: {
    SNIPPET_LINES: 2,
    SNIPPET_CHARS: 150,
  },
  MATCH: {
    MIN_WORDS: 3,
    MAX_SEARCH_WORDS: 6,
  },
} as const;
