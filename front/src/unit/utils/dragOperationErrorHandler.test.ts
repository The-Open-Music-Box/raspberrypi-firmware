import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  handleDragError,
  getDragErrorMessage,
  validateDragContext,
  DragOperationError
} from '@/utils/dragOperationErrorHandler'

vi.mock('@/utils/logger', () => ({
  logger: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn()
  }
}))

describe('dragOperationErrorHandler', () => {
  const baseCtx = {
    operation: 'move',
    playlistId: 'p1',
    sourcePlaylistId: 'p0',
    trackNumber: 1,
    component: 'Comp'
  } as any

  it('handleDragError wraps generic errors and logs at levels', () => {
    const err = handleDragError(new Error('x'), baseCtx, { logLevel: 'debug' })
    expect(err).toBeInstanceOf(DragOperationError)
    handleDragError(err, baseCtx, { logLevel: 'info' })
    handleDragError(err, baseCtx, { logLevel: 'warn' })
    handleDragError(err, baseCtx, { logLevel: 'error' })
  })

  it('getDragErrorMessage returns friendly text', () => {
    expect(getDragErrorMessage('reorder')).toMatch(/reorder/)
    expect(getDragErrorMessage('move')).toMatch(/move/)
    expect(getDragErrorMessage('delete')).toMatch(/delete/)
    expect(getDragErrorMessage('add')).toMatch(/add/)
  })

  it('validateDragContext validates required fields and operation specifics', () => {
    // Missing operation
    expect(validateDragContext({})).toBeNull()
    // Missing playlistId
    expect(validateDragContext({ operation: 'move', component: 'C' } as any)).toBeNull()
    // Missing component
    expect(validateDragContext({ operation: 'move', playlistId: 'p' } as any)).toBeNull()
    // Move requires sourcePlaylistId and trackNumber
    expect(validateDragContext({ operation: 'move', playlistId: 'p', component: 'C' } as any)).toBeNull()
    // Reorder requires trackNumbers
    expect(validateDragContext({ operation: 'reorder', playlistId: 'p', component: 'C' } as any)).toBeNull()

    const okMove = validateDragContext({ operation: 'move', playlistId: 'p', component: 'C', sourcePlaylistId: 's', trackNumber: 1 })
    expect(okMove).not.toBeNull()
    const okReorder = validateDragContext({ operation: 'reorder', playlistId: 'p', component: 'C', trackNumbers: [1,2] })
    expect(okReorder).not.toBeNull()

    // Missing trackNumber branch for move
    const missingNum = validateDragContext({ operation: 'move', playlistId: 'p', component: 'C', sourcePlaylistId: 's' } as any)
    expect(missingNum).toBeNull()
  })
})
