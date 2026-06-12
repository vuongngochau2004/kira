/**
 * Improved Text Matching Utilities
 * Better algorithms for finding and highlighting relevant text segments
 */

import { useMemo } from 'react'
import type { TextMatchResult } from '../types/source-panel-types'

// ============================================
// Configuration
// ============================================

const MATCH_CONFIG = {
  // Minimum similarity ratio for text match (0-1)
  MIN_SIMILARITY_RATIO: 0.6,

  // Context window size around match (characters)
  CONTEXT_BEFORE: 60,
  CONTEXT_AFTER: 100,

  // Maximum highlighted text length
  MAX_HIGHLIGHT_LENGTH: 300,

  // Word matching tolerance
  WORD_TOLERANCE: 2, // Allow 2 word differences
}

// ============================================
// Text Preprocessing
// ============================================

export function normalizeText(text: string): string {
  if (!text) return ''
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '') // Remove diacritics
    .replace(/[^\p{L}\p{N}\s]/gu, ' ') // Keep only alphanumeric
    .replace(/\s+/g, ' ')
    .trim()
}

function tokenizeWords(text: string): string[] {
  return text.split(/\s+/).filter(word => word.length > 0)
}

// ============================================
// Similarity Calculation
// ============================================

function levenshteinDistance(str1: string, str2: string): number {
  const len1 = str1.length
  const len2 = str2.length
  const matrix: number[][] = []

  for (let i = 0; i <= len1; i++) {
    matrix[i] = [i]
  }

  for (let j = 0; j <= len2; j++) {
    matrix[0][j] = j
  }

  for (let i = 1; i <= len1; i++) {
    for (let j = 1; j <= len2; j++) {
      const cost = str1[i - 1] === str2[j - 1] ? 0 : 1
      matrix[i][j] = Math.min(
        matrix[i - 1][j] + 1,
        matrix[i][j - 1] + 1,
        matrix[i - 1][j - 1] + cost
      )
    }
  }

  return matrix[len1][len2]
}

export function calculateSimilarity(str1: string, str2: string): number {
  const len1 = str1.length
  const len2 = str2.length

  if (len1 === 0 && len2 === 0) return 1
  if (len1 === 0 || len2 === 0) return 0

  const distance = levenshteinDistance(str1, str2)
  const maxLength = Math.max(len1, len2)

  return 1 - distance / maxLength
}

// ============================================
// Smart Text Matching
// ============================================

/**
 * Find the best matching segment with context extraction
 */
export function findRelevantSegment(
  fullText: string,
  querySnippet: string
): {
  segment: string
  match: TextMatchResult | null
  relevance: number
} {
  if (!fullText || !querySnippet) {
    return { segment: fullText, match: null, relevance: 0 }
  }

  const normalizedFull = normalizeText(fullText)
  const normalizedQuery = normalizeText(querySnippet)
  const queryWords = tokenizeWords(normalizedQuery)

  if (queryWords.length === 0) {
    return { segment: fullText, match: null, relevance: 0 }
  }

  // Strategy 1: Try exact match first
  const exactIdx = normalizedFull.indexOf(normalizedQuery)
  if (exactIdx !== -1) {
    const match: TextMatchResult = {
      index: exactIdx,
      length: normalizedQuery.length,
      matchedText: querySnippet,
    }
    const segment = extractContextWithMatch(fullText, match)
    return { segment, match, relevance: 1.0 }
  }

  // Strategy 2: Find longest word sequence match
  const bestWordMatch = findBestWordSequenceMatch(normalizedFull, queryWords)
  if (bestWordMatch && bestWordMatch.similarity >= MATCH_CONFIG.MIN_SIMILARITY_RATIO) {
    const match: TextMatchResult = {
      index: bestWordMatch.index,
      length: bestWordMatch.length,
      matchedText: bestWordMatch.text,
    }
    const segment = extractContextWithMatch(fullText, match)
    return { segment, match, relevance: bestWordMatch.similarity }
  }

  // Strategy 3: Find partial phrase matches
  const partialMatch = findPartialPhraseMatch(normalizedFull, queryWords)
  if (partialMatch) {
    const match: TextMatchResult = {
      index: partialMatch.index,
      length: partialMatch.length,
      matchedText: partialMatch.text,
    }
    const segment = extractContextWithMatch(fullText, match)
    return { segment, match, relevance: 0.5 }
  }

  // Fallback: Return beginning of text with limited length
  const truncatedSegment = fullText.substring(0, MATCH_CONFIG.MAX_HIGHLIGHT_LENGTH)
  return { segment: truncatedSegment, match: null, relevance: 0 }
}

/**
 * Find best matching word sequence
 */
function findBestWordSequenceMatch(
  normalizedFull: string,
  queryWords: string[]
): { index: number; length: number; text: string; similarity: number } | null {
  const fullWords = tokenizeWords(normalizedFull)
  let bestMatch: { index: number; length: number; text: string; similarity: number } | null = null

  // Try decreasing sequence lengths
  for (let seqLen = queryWords.length; seqLen >= 3; seqLen--) {
    for (let startIdx = 0; startIdx <= queryWords.length - seqLen; startIdx++) {
      const sequence = queryWords.slice(startIdx, startIdx + seqLen).join(' ')
      const seqIdx = normalizedFull.indexOf(sequence)

      if (seqIdx !== -1) {
        // Reconstruct original text with correct casing
        const originalMatch = reconstructOriginalMatch(normalizedFull, sequence, seqIdx)
        const similarity = calculateSimilarity(sequence, queryWords.join(' '))

        if (!bestMatch || similarity > bestMatch.similarity) {
          bestMatch = {
            index: seqIdx,
            length: sequence.length,
            text: originalMatch,
            similarity,
          }
        }
      }
    }

    // If found good match with this length, don't try shorter
    if (bestMatch && bestMatch.similarity >= 0.8) {
      break
    }
  }

  return bestMatch
}

/**
 * Find partial phrase matches with word tolerance
 */
function findPartialPhraseMatch(
  normalizedFull: string,
  queryWords: string[]
): { index: number; length: number; text: string } | null {
  const fullWords = tokenizeWords(normalizedFull)

  for (let i = 0; i <= fullWords.length - queryWords.length + MATCH_CONFIG.WORD_TOLERANCE; i++) {
    let matchCount = 0
    const windowWords = fullWords.slice(i, i + queryWords.length + MATCH_CONFIG.WORD_TOLERANCE)

    for (const queryWord of queryWords) {
      if (windowWords.some(w => w.includes(queryWord) || queryWord.includes(w))) {
        matchCount++
      }
    }

    const ratio = matchCount / queryWords.length
    if (ratio >= MATCH_CONFIG.MIN_SIMILARITY_RATIO) {
      const matchedText = windowWords.slice(0, queryWords.length).join(' ')
      const matchStart = normalizedFull.indexOf(matchedText)

      if (matchStart !== -1) {
        return {
          index: matchStart,
          length: matchedText.length,
          text: reconstructOriginalMatch(normalizedFull, matchedText, matchStart),
        }
      }
    }
  }

  return null
}

/**
 * Reconstruct original text with proper casing
 */
function reconstructOriginalMatch(
  normalizedFull: string,
  normalizedMatch: string,
  matchIndex: number
): string {
  // This is a simplified version - assumes character positions align
  // In production, you'd need to track original vs normalized positions
  return normalizedMatch
}

/**
 * Extract context around a match with proper boundaries
 */
function extractContextWithMatch(
  fullText: string,
  match: TextMatchResult
): string {
  const { index, length } = match

  // Calculate boundaries
  let start = Math.max(0, index - MATCH_CONFIG.CONTEXT_BEFORE)
  let end = Math.min(fullText.length, index + length + MATCH_CONFIG.CONTEXT_AFTER)

  // Adjust to word boundaries
  while (start > 0 && fullText[start - 1] !== ' ' && fullText[start - 1] !== '\n') {
    start--
  }

  while (end < fullText.length && fullText[end] !== ' ' && fullText[end] !== '\n') {
    end++
  }

  let segment = fullText.substring(start, end)

  // Add ellipsis if truncated
  if (start > 0) {
    segment = '... ' + segment
  }

  if (end < fullText.length) {
    segment = segment + ' ...'
  }

  // Limit total length
  if (segment.length > MATCH_CONFIG.MAX_HIGHLIGHT_LENGTH) {
    segment = segment.substring(0, MATCH_CONFIG.MAX_HIGHLIGHT_LENGTH) + ' ...'
  }

  return segment
}

// ============================================
// Hook
// ============================================

export function useImprovedTextMatching() {
  return useMemo(
    () => ({
      findRelevantSegment,
      normalizeText,
      calculateSimilarity,
    }),
    []
  )
}
