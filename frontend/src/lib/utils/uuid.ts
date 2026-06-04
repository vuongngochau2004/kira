/**
 * Validate UUID v4 format
 * @param uuid - String to validate
 * @returns true if valid UUID v4 format
 */
export function isValidUUID(uuid: string): boolean {
  if (!uuid || typeof uuid !== 'string') return false
  return /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(uuid)
}

/**
 * Extract and validate UUID from various sources
 * @param value - Value to extract UUID from
 * @returns Valid UUID string or null
 */
export function extractUUID(value: string | null | undefined): string | null {
  if (!value) return null

  // Direct UUID
  if (isValidUUID(value)) return value

  // Try to extract UUID from string
  const uuidMatch = value.match(/([0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})/i)
  return uuidMatch ? uuidMatch[1] : null
}
