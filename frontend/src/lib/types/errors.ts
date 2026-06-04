/**
 * Error types for conversation operations
 */

export enum ConversationErrorType {
  CREATE_FAILED = 'CREATE_FAILED',
  NETWORK_TIMEOUT = 'NETWORK_TIMEOUT',
  INVALID_CONVERSATION_ID = 'INVALID_CONVERSATION_ID',
  STREAM_ERROR = 'STREAM_ERROR',
  QUEUE_FLUSH_FAILED = 'QUEUE_FLUSH_FAILED',
}

export class ConversationError extends Error {
  constructor(
    public type: ConversationErrorType,
    message: string,
    public retryable: boolean = true,
    public userMessage?: string
  ) {
    super(message)
    this.name = 'ConversationError'
  }
}

/**
 * Get user-friendly error message
 */
export function getErrorUserMessage(error: ConversationError): string {
  switch (error.type) {
    case ConversationErrorType.CREATE_FAILED:
      return 'Failed to create conversation. Please try again.'
    case ConversationErrorType.NETWORK_TIMEOUT:
      return 'Network timeout. Please check your connection.'
    case ConversationErrorType.INVALID_CONVERSATION_ID:
      return 'Invalid conversation. Starting a new one.'
    case ConversationErrorType.STREAM_ERROR:
      return 'Connection interrupted. Your message was sent.'
    case ConversationErrorType.QUEUE_FLUSH_FAILED:
      return 'Some messages failed to send. Please retry.'
    default:
      return 'Something went wrong. Please try again.'
  }
}
