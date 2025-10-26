import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { compressImage, generateSrcSet, lazyLoadImage, preloadImage, supportsWebP } from '@/utils/imageUtils'

describe('imageUtils', () => {
  const OriginalImage = global.Image
  let toRevoke: string[] = []

  beforeEach(() => {
    vi.restoreAllMocks()

    // Mock URL.createObjectURL/revokeObjectURL
    vi.spyOn(URL, 'createObjectURL').mockImplementation(() => {
      const url = 'blob:mock'
      toRevoke.push(url)
      return url
    })
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation((u: string) => {
      toRevoke = toRevoke.filter(x => x !== u)
    })

    // Mock canvas and context
    const originalCreate = document.createElement.bind(document)
    vi.spyOn(document, 'createElement').mockImplementation(((tag: string) => {
      if (tag === 'canvas') {
        return {
          width: 0,
          height: 0,
          getContext: () => ({ drawImage: vi.fn() }),
          toBlob: (cb: (b: Blob | null) => void) => cb(new Blob(['x'], { type: 'image/jpeg' }))
        } as any
      }
      return originalCreate(tag as any)
    }) as any)

    // Mock Image to trigger onload and onerror flows
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    // @ts-ignore
    global.Image = class MockImage {
      onload: (() => void) | null = null
      onerror: (() => void) | null = null
      width = 1200
      height = 800
      set src(_v: string) {
        // call onload on next tick
        setTimeout(() => this.onload && this.onload(), 0)
      }
    } as any

    // Mock IntersectionObserver
    const observe = vi.fn()
    const unobserve = vi.fn()
    // @ts-ignore
    global.IntersectionObserver = vi.fn(cb => ({ observe, unobserve, disconnect: vi.fn(), takeRecords: vi.fn() })) as any
  })

  afterEach(() => {
    global.Image = OriginalImage
  })

  it('compressImage resolves with blob', async () => {
    const blob = await compressImage(new File(['a'], 'a.jpg', { type: 'image/jpeg' }))
    expect(blob).toBeInstanceOf(Blob)
  })

  it('compressImage portrait branch and toBlob failure', async () => {
    // Override Image to portrait dimensions
    const Prev = global.Image as any
    global.Image = class extends (Prev as any) {
      width = 600
      height = 1200
      set src(_v: string) { setTimeout(() => this.onload && this.onload(), 0) }
    } as any

    const originalCreate = document.createElement.bind(document)
    const spy = vi.spyOn(document, 'createElement').mockImplementation(((tag: string) => {
      if (tag === 'canvas') {
        return {
          width: 0,
          height: 0,
          getContext: () => ({ drawImage: vi.fn() }),
          toBlob: (cb: (b: Blob | null) => void) => cb(null)
        } as any
      }
      return originalCreate(tag as any)
    }) as any)

    await expect(compressImage(new File(['a'], 'a.jpg', { type: 'image/jpeg' }))).rejects.toThrow(/Failed to compress/)
    spy.mockRestore()
    global.Image = Prev
  })

  it('generateSrcSet builds correct string', () => {
    const s = generateSrcSet('/img', [1, 2])
    expect(s).toBe('/img?w=1 1w, /img?w=2 2w')
  })

  it('lazyLoadImage sets src when intersecting', () => {
    const img = document.createElement('img') as HTMLImageElement
    img.classList = { remove: vi.fn() } as any
    lazyLoadImage(img, '/x')
    // Invoke callback
    const inst = (global as any).IntersectionObserver.mock.results[0].value
    inst.observe(img)
    const cb = (global as any).IntersectionObserver.mock.calls[0][0]
    cb([{ isIntersecting: true }])
    expect((img as any).src.endsWith('/x')).toBe(true)
  })

  it('lazyLoadImage falls back when IntersectionObserver missing', () => {
    const prev = (global as any).IntersectionObserver
    // Remove IntersectionObserver
    // @ts-ignore
    delete (global as any).IntersectionObserver
    const img = document.createElement('img') as HTMLImageElement
    lazyLoadImage(img, '/y')
    expect((img as any).src.endsWith('/y')).toBe(true)
    // restore a basic stub to not affect other tests
    ;(global as any).IntersectionObserver = prev
  })

  it('preloadImage resolves and supportsWebP returns boolean', async () => {
    await expect(preloadImage('/a')).resolves.toBeUndefined()

    // Override Image for this call to emulate height===2 on decode
    const Prev = global.Image as any
    // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
    global.Image = class extends (Prev as any) { constructor(){ super(); (this as any).height = 2 } } as any
    await expect(supportsWebP()).resolves.toBe(true)
    global.Image = Prev
  })
})
