/**
 * Centralized utility for generating client operation IDs
 * Eliminates duplication across API service methods
 */

/**
 * Generates a unique client operation ID for request tracking and deduplication
 * @param operation - The operation name (e.g., 'create_playlist', 'delete_track')
 * @returns A unique operation ID string
 */
export function generateClientOpId(operation: string): string {
  const timestamp = Date.now()
  let randomSuffix = Math.random().toString(36).substr(2, 9)
  
  // Handle edge case where Math.random() returns 0, resulting in empty suffix
  if (randomSuffix.length === 0) {
    randomSuffix = '000000000' // 9 zeros as fallback
  }
  
  return `${operation}_${timestamp}_${randomSuffix}`
}

/**
 * Validates a client operation ID format
 * @param clientOpId - The operation ID to validate
 * @returns True if valid, false otherwise
 */
export function validateClientOpId(clientOpId: string): boolean {
  if (!clientOpId || typeof clientOpId !== 'string') {
    return false
  }
  
  // Should match pattern: operation_timestamp_random
  // Find the last two underscores to separate operation_name from timestamp and random_suffix
  const lastUnderscoreIndex = clientOpId.lastIndexOf('_')
  if (lastUnderscoreIndex === -1) return false
  
  const secondLastUnderscoreIndex = clientOpId.lastIndexOf('_', lastUnderscoreIndex - 1)
  if (secondLastUnderscoreIndex === -1) return false
  
  // Extract the timestamp part (between second-last and last underscore)
  const timestampPart = clientOpId.substring(secondLastUnderscoreIndex + 1, lastUnderscoreIndex)
  
  // Extract the random suffix part (after last underscore)
  const randomSuffixPart = clientOpId.substring(lastUnderscoreIndex + 1)
  
  // Validate timestamp is numeric and not empty, and random suffix is not empty
  return timestampPart.length > 0 && !isNaN(Number(timestampPart)) && randomSuffixPart.length > 0
}

/**
 * Extracts the operation name from a client operation ID
 * @param clientOpId - The operation ID
 * @returns The operation name or null if invalid
 */
export function extractOperationName(clientOpId: string): string | null {
  if (!validateClientOpId(clientOpId)) {
    return null
  }
  
  // Find the last two underscores to separate operation_name from timestamp and random_suffix
  const lastUnderscoreIndex = clientOpId.lastIndexOf('_')
  const secondLastUnderscoreIndex = clientOpId.lastIndexOf('_', lastUnderscoreIndex - 1)
  
  // Return everything before the second-last underscore (the operation name)
  return clientOpId.substring(0, secondLastUnderscoreIndex)
}
