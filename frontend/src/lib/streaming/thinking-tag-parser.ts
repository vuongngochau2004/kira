/**
 * ThinkingTagParser - Pure functions for parsing <thinking> tags from streaming content
 *
 * Design principles:
 * - Stateless: No side effects, no mutations
 * - Single Responsibility: Only parse thinking tags, nothing else
 * - Testable: Pure functions, easy to unit test
 * - Incremental: Works with partial/chunked data during streaming
 */

// ==================== Types ====================

export interface ParseResult {
  /** Extracted reasoning content (inside <thinking> tags) */
  reasoning: string
  /** Content outside <thinking> tags */
  content: string
  /** Remaining unprocessed text (for stateful parsers) */
  remaining: string
  /** Are we currently inside <thinking> tag? */
  isInThinkingTag: boolean
  /** Did we complete a thinking section? */
  completedThinking: boolean
}

export interface ParseState {
  /** Current parsing state */
  isInThinkingTag: boolean
  /** Accumulated reasoning content */
  reasoning: string
  /** Accumulated regular content */
  content: string
}

// ==================== Constants ====================

const THINKING_OPEN = '<thinking>'
const THINKING_CLOSE = '</thinking>'
const THINKING_OPEN_LEN = THINKING_OPEN.length
const THINKING_CLOSE_LEN = THINKING_CLOSE.length

// ==================== Pure Functions ====================

/**
 * Parse a single content chunk and extract thinking tags
 *
 * This function handles streaming scenarios where:
 * - Chunks may contain partial tags
 * - Tags may span multiple chunks
 * - Multiple thinking sections may exist
 *
 * @param chunk - The content chunk to parse
 * @param isInThinkingTag - Whether we're currently inside a <thinking> tag
 * @returns Parse result with separated reasoning and content
 *
 * @example
 * ```ts
 * // First chunk with opening tag
 * parseChunk("<thinking>Hello", false)
 * // → { reasoning: "Hello", content: "", isInThinkingTag: true, ... }
 *
 * // Middle chunk inside tag
 * parseChunk(" World", true)
 * // → { reasoning: " World", content: "", isInThinkingTag: true, ... }
 *
 * // Closing tag
 * parseChunk("</thinking>Response", true)
 * // → { reasoning: "", content: "Response", isInThinkingTag: false, completedThinking: true, ... }
 * ```
 */
export function parseChunk(chunk: string, isInThinkingTag: boolean): ParseResult {
  let reasoning = ''
  let content = ''
  let remaining = chunk
  let completedThinking = false

  while (remaining.length > 0) {
    if (isInThinkingTag) {
      // We're inside <thinking>, look for closing tag
      const closeIndex = remaining.indexOf(THINKING_CLOSE)

      if (closeIndex === -1) {
        // No closing tag, rest is reasoning
        reasoning += remaining
        remaining = ''
      } else {
        // Found closing tag
        reasoning += remaining.slice(0, closeIndex)
        isInThinkingTag = false
        completedThinking = true
        remaining = remaining.slice(closeIndex + THINKING_CLOSE_LEN)
      }
    } else {
      // We're outside, look for opening tag
      const openIndex = remaining.indexOf(THINKING_OPEN)

      if (openIndex === -1) {
        // No opening tag, rest is content
        content += remaining
        remaining = ''
      } else {
        // Found opening tag
        content += remaining.slice(0, openIndex)
        isInThinkingTag = true
        remaining = remaining.slice(openIndex + THINKING_OPEN_LEN)
      }
    }
  }

  return {
    reasoning,
    content,
    remaining: '',
    isInThinkingTag,
    completedThinking,
  }
}

/**
 * Parse complete content (non-streaming)
 * Useful for parsing saved messages from backend
 *
 * @param fullContent - Complete content with thinking tags
 * @returns Parsed result with reasoning and content separated
 */
export function parseFullContent(fullContent: string): { reasoning: string; content: string } {
  const result = parseChunk(fullContent, false)

  // For complete content, we should not be in the middle of a tag
  // If we are, it means incomplete tags - treat as content
  if (result.isInThinkingTag) {
    return {
      reasoning: '',
      content: fullContent,
    }
  }

  return {
    reasoning: result.reasoning,
    content: result.content,
  }
}

/**
 * Strip thinking tags from content (for display fallback)
 * This removes the tags but keeps both reasoning and content
 */
export function stripThinkingTags(content: string): string {
  const parsed = parseFullContent(content)

  // If we have reasoning, include it as gray text
  if (parsed.reasoning) {
    return `${parsed.reasoning}\n\n${parsed.content}`.trim()
  }

  return parsed.content
}

// ==================== Stateful Parser (for streaming) ====================

/**
 * Create a stateful parser for streaming scenarios
 * Maintains parsing state across multiple chunks
 *
 * @example
 * ```ts
 * const parser = createStreamingParser()
 *
 * for await (const chunk of stream) {
 *   const result = parser.feed(chunk)
 *   console.log('Reasoning so far:', result.reasoning)
 *   console.log('Content so far:', result.content)
 * }
 *
 * const final = parser.finalize()
 * ```
 */
export function createStreamingParser() {
  let state: ParseState = {
    isInThinkingTag: false,
    reasoning: '',
    content: '',
  }

  return {
    /**
     * Feed a chunk to the parser
     */
    feed(chunk: string): ParseState {
      const result = parseChunk(chunk, state.isInThinkingTag)

      state.reasoning += result.reasoning
      state.content += result.content
      state.isInThinkingTag = result.isInThinkingTag

      return { ...state }
    },

    /**
     * Get current state without consuming
     */
    getState(): ParseState {
      return { ...state }
    },

    /**
     * Reset parser to initial state
     */
    reset(): void {
      state = {
        isInThinkingTag: false,
        reasoning: '',
        content: '',
      }
    },

    /**
     * Finalize parsing and get complete result
     */
    finalize(): { reasoning: string; content: string } {
      return {
        reasoning: state.reasoning,
        content: state.content,
      }
    },
  }
}
