import { describe, it, expect, vi, beforeEach } from 'vitest'
import { logger } from '@/utils/logger'

describe('logger', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('respects log levels (debug/info/warn/error)', () => {
    const spyErr = vi.spyOn(console, 'error').mockImplementation(() => {})
    const spyWarn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const spyInfo = vi.spyOn(console, 'info').mockImplementation(() => {})
    const spyLog = vi.spyOn(console, 'log').mockImplementation(() => {})

    // Force most verbose level
    ;(logger as any).currentLevel = 3
    logger.debug('d')
    logger.info('i')
    logger.warn('w')
    logger.error('e')
    expect(spyLog).toHaveBeenCalled()
    expect(spyInfo).toHaveBeenCalled()
    expect(spyWarn).toHaveBeenCalled()
    expect(spyErr).toHaveBeenCalled()

    // Restrict to WARN only
    ;(logger as any).currentLevel = 1
    spyLog.mockClear(); spyInfo.mockClear(); spyWarn.mockClear(); spyErr.mockClear()
    logger.debug('d2')
    logger.info('i2')
    logger.warn('w2')
    logger.error('e2')
    expect(spyLog).not.toHaveBeenCalled()
    expect(spyInfo).not.toHaveBeenCalled()
    expect(spyWarn).toHaveBeenCalled()
    expect(spyErr).toHaveBeenCalled()

    // Exercise branches without data payloads
    spyLog.mockClear(); spyInfo.mockClear(); spyWarn.mockClear(); spyErr.mockClear()
    ;(logger as any).currentLevel = 3
    logger.debug('d-msg')
    logger.debug('d-data', { d: 1 })
    logger.info('i-msg', { i: 1 })
    logger.warn('w-msg', { w: 1 })
    logger.error('e-msg', { e: 1 })
    expect(spyLog).toHaveBeenCalledWith(expect.stringContaining('DEBUG'),)
    expect(spyInfo).toHaveBeenCalledWith(expect.stringContaining('INFO'), { i: 1 })
    expect(spyWarn).toHaveBeenCalledWith(expect.stringContaining('WARN'), { w: 1 })
    expect(spyErr).toHaveBeenCalledWith(expect.stringContaining('ERROR'), { e: 1 })
  })
})
