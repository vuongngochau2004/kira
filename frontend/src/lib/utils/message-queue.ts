/**
 * Simple FIFO queue for pending conversation messages
 */

export interface QueuedMessage {
  id: string
  content: string
  timestamp: Date
  assistantId?: string  // Optional: Track corresponding assistant message ID
}

export class MessageQueue {
  private queue: QueuedMessage[] = []
  private isFlushing = false

  /**
   * Add message to queue
   */
  enqueue(message: QueuedMessage): void {
    this.queue.push(message)
  }

  /**
   * Remove and return first message
   */
  dequeue(): QueuedMessage | undefined {
    return this.queue.shift()
  }

  /**
   * Get all queued messages
   */
  getAll(): QueuedMessage[] {
    return [...this.queue]
  }

  /**
   * Clear queue
   */
  clear(): void {
    this.queue = []
  }

  /**
   * Get queue size
   */
  size(): number {
    return this.queue.length
  }

  /**
   * Check if queue is empty
   */
  isEmpty(): boolean {
    return this.queue.length === 0
  }

  /**
   * Flush queue with callback for each message
   * Processes messages sequentially in order
   */
  async flush(callback: (message: QueuedMessage) => Promise<void>): Promise<void> {
    if (this.isFlushing) {
      return // Already flushing
    }

    if (this.isEmpty()) {
      return // Nothing to flush
    }

    this.isFlushing = true

    try {
      while (!this.isEmpty()) {
        const message = this.dequeue()
        if (message) {
          await callback(message)
        }
      }
    } finally {
      this.isFlushing = false
    }
  }
}
