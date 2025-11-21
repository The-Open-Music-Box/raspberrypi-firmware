import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiClient, ApiResponseHandler } from '@/services/api/apiClient'

// Silence logs
vi.mock('@/utils/logger', () => ({
  logger: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn()
  }
}))

describe('apiClient interceptors', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('request interceptor attaches metadata and logs', async () => {
    const req = { method: 'get', url: '/x', headers: {} } as any
    const fulfilled = (apiClient.interceptors.request as any).handlers[0].fulfilled
    const out = await fulfilled(req)
    expect(out.metadata?.start).toBeDefined()
  })

  it('request interceptor rejected path logs and rejects', async () => {
    const rejected = (apiClient.interceptors.request as any).handlers[0].rejected
    const err = { message: 'req-oops' }
    await expect(rejected(err)).rejects.toEqual(err)
  })

  it('ApiResponseHandler.handleError covers config error branch', () => {
    const err = { config: {}, message: 'bad setup' }
    expect(() => ApiResponseHandler.handleError(err)).toThrow(/Request configuration error/)
  })

  it('response interceptor fulfilled path logs and returns response', async () => {
    const res = {
      config: { method: 'get', url: '/x', metadata: { start: Date.now() - 10 } },
      status: 200
    } as any
    const fulfilled = (apiClient.interceptors.response as any).handlers[0].fulfilled
    const out = await fulfilled(res)
    expect(out).toBe(res)
  })

  it('response interceptor rejected path delegates to ApiResponseHandler.handleError', () => {
    const spy = vi.spyOn(ApiResponseHandler, 'handleError').mockImplementation((err: any) => {
      throw new Error('normalized')
    })
    const rejected = (apiClient.interceptors.response as any).handlers[0].rejected
    expect(() => rejected({ config: {}, message: 'boom' } as any)).toThrow('normalized')
    expect(spy).toHaveBeenCalled()
  })
})
