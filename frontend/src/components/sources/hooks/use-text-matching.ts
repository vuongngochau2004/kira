/**
 * Text Matching Utilities Hook
 * Utilities for finding and highlighting text matches
 */

import { useMemo } from 'react'
import type { TextMatchResult, DocumentChunk } from '../types/source-panel-types'
import { SOURCE_PANEL_CONSTANTS } from '../types/source-panel-types'

// ============================================
// Text Cleaning
// ============================================

export function cleanStringForMatching(str: string): string {
  if (!str) return ''
  return str
    .toLowerCase()
    .replace(/[\s\r\n\t]+/g, ' ')
    .replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?"']/g, '')
    .trim()
}

// ============================================
// Match Finding
// ============================================

export function findLongestMatch(
  content: string,
  snippet: string
): TextMatchResult | null {
  const cleanedC = content.toLowerCase()
  const cleanedS = snippet.toLowerCase()

  // Try exact match first
  const exactIdx = cleanedC.indexOf(cleanedS)
  if (exactIdx !== -1) {
    return {
      index: exactIdx,
      length: snippet.length,
      matchedText: snippet,
    }
  }

  // Find longest word sub-segment that matches
  const words = snippet.split(/\s+/).filter(Boolean)
  if (words.length === 0) return null

  const MIN_WORDS = SOURCE_PANEL_CONSTANTS.MATCH.MIN_WORDS

  // Check word segments of decreasing length
  for (let len = words.length - 1; len >= MIN_WORDS; len--) {
    for (let start = 0; start <= words.length - len; start++) {
      const subPhrase = words.slice(start, start + len).join(' ')
      const idx = cleanedC.indexOf(subPhrase.toLowerCase())
      if (idx !== -1) {
        return {
          index: idx,
          length: subPhrase.length,
          matchedText: subPhrase,
        }
      }
    }
  }

  return null
}

// ============================================
// Search Phrase Extraction
// ============================================

export function getCleanSearchPhrase(snippet: string): string {
  if (!snippet) return ''

  const words = snippet
    .replace(/[^\p{L}\p{N}\s]/gu, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean)

  const MAX_WORDS = SOURCE_PANEL_CONSTANTS.MATCH.MAX_SEARCH_WORDS
  return words.slice(0, MAX_WORDS).join(' ')
}

// ============================================
// Chunk Grouping by Page
// ============================================

export function groupChunksByPage(chunks: DocumentChunk[]): Record<number, DocumentChunk[]> {
  const pages: Record<number, DocumentChunk[]> = {}

  chunks.forEach((chunk) => {
    const page = chunk.metadata?.page_number || chunk.metadata?.page || 1
    if (!pages[page]) {
      pages[page] = []
    }
    pages[page].push(chunk)
  })

  return pages
}

// ============================================
// Hook
// ============================================

interface UseTextMatchingResult {
  cleanStringForMatching: (str: string) => string
  findLongestMatch: (content: string, snippet: string) => TextMatchResult | null
  getCleanSearchPhrase: (snippet: string) => string
  groupChunksByPage: (chunks: any[]) => Record<number, any[]>
}

export function useTextMatching(): UseTextMatchingResult {
  return useMemo(
    () => ({
      cleanStringForMatching,
      findLongestMatch,
      getCleanSearchPhrase,
      groupChunksByPage,
    }),
    []
  )
}
