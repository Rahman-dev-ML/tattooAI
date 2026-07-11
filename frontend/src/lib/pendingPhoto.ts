const KEY = 'tattoo-pending-body-photo'
const LOG = process.env.NODE_ENV === 'development'

function log(...args: unknown[]) {
  if (LOG) console.log('[pendingPhoto]', ...args)
}

export const FLOW_RESULT_KEY = (flowId: string) => `tattoo-result-${flowId}`

/** In-memory handoff — survives React Strict Mode double-mount. NOT cleared on read. */
let handoffFile: File | null = null
let handoffKey: string | null = null

function fileKey(file: File): string {
  return `${file.name}:${file.size}:${file.lastModified}`
}

/** Resize/compress so sessionStorage (≈5MB cap) does not drop the photo on mobile. */
async function fileToStorableDataUrl(file: File): Promise<string> {
  if (typeof window === 'undefined') {
    return fileToDataUrl(file)
  }

  try {
    const bitmap = await createImageBitmap(file)
    const maxDim = 1600
    let { width, height } = bitmap
    if (width > maxDim || height > maxDim) {
      const scale = maxDim / Math.max(width, height)
      width = Math.round(width * scale)
      height = Math.round(height * scale)
    }

    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      bitmap.close()
      return fileToDataUrl(file)
    }
    ctx.drawImage(bitmap, 0, 0, width, height)
    bitmap.close()

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, 'image/jpeg', 0.88)
    )
    if (!blob) return fileToDataUrl(file)

    return await blobToDataUrl(blob)
  } catch (err) {
    log('compress failed, using raw file', err)
    return fileToDataUrl(file)
  }
}

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = () => reject(new Error('Failed to read photo file'))
    reader.readAsDataURL(file)
  })
}

function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = () => reject(new Error('Failed to encode photo'))
    reader.readAsDataURL(blob)
  })
}

function dataUrlToFile(
  dataUrl: string,
  name: string,
  type: string,
  lastModified: number
): File {
  const [header, base64] = dataUrl.split(',')
  const mime = header.match(/data:([^;]+)/)?.[1] || type || 'image/jpeg'
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return new File([bytes], name, { type: mime, lastModified })
}

export function hasPendingBodyPhoto(): boolean {
  if (handoffFile) return true
  if (typeof window === 'undefined') return false
  return sessionStorage.getItem(KEY) !== null
}

/** Read handoff without clearing — safe for multiple React mounts. */
export function getHandoffBodyPhoto(): File | null {
  if (handoffFile) {
    log('getHandoff (memory)', handoffFile.name)
    return handoffFile
  }
  return null
}

/** Call after generate succeeds or user starts over. */
export function clearHandoffBodyPhoto(): void {
  handoffFile = null
  handoffKey = null
  if (typeof window !== 'undefined') {
    sessionStorage.removeItem(KEY)
  }
  log('handoff cleared')
}

let storeInflight: Promise<void> | null = null

/**
 * Store photo for homepage → flow handoff.
 * Sets in-memory handoff IMMEDIATELY; sessionStorage is async backup for page reload.
 */
export async function storePendingBodyPhoto(file: File): Promise<void> {
  const key = fileKey(file)

  // Always update memory handoff right away (survives navigation + Strict Mode)
  handoffFile = file
  handoffKey = key
  log('handoff set (memory)', key, `${(file.size / 1024).toFixed(0)}KB`)

  if (storeInflight && handoffKey === key) {
    return storeInflight
  }

  storeInflight = (async () => {
    const dataUrl = await fileToStorableDataUrl(file)
    try {
      sessionStorage.setItem(
        KEY,
        JSON.stringify({
          dataUrl,
          name: file.name.replace(/\.\w+$/, '') + '.jpg',
          type: 'image/jpeg',
          lastModified: file.lastModified,
        })
      )
      log('sessionStorage backup OK', `${(dataUrl.length / 1024).toFixed(0)}KB`)
    } catch (err) {
      // Memory handoff still works — sessionStorage is only a reload fallback
      console.warn('[pendingPhoto] sessionStorage backup failed (memory handoff still OK):', err)
    }
  })().finally(() => {
    storeInflight = null
  })

  return storeInflight
}

export function clearPendingBodyPhoto(): void {
  clearHandoffBodyPhoto()
}

/** Fallback: restore from sessionStorage if memory handoff is empty (page reload). */
export async function restorePendingBodyPhotoFromStorage(): Promise<File | null> {
  if (typeof window === 'undefined') return null
  if (handoffFile) return handoffFile

  const raw = sessionStorage.getItem(KEY)
  if (!raw) {
    log('storage restore: nothing found')
    return null
  }

  try {
    const { dataUrl, name, type, lastModified } = JSON.parse(raw) as {
      dataUrl: string
      name: string
      type: string
      lastModified: number
    }
    const file = dataUrlToFile(dataUrl, name, type, lastModified)
    handoffFile = file
    handoffKey = fileKey(file)
    log('storage restore OK', name, `${(file.size / 1024).toFixed(0)}KB`)
    return file
  } catch (err) {
    console.error('[pendingPhoto] storage restore failed:', err)
    return null
  }
}

/** @deprecated Use getHandoffBodyPhoto — kept for any legacy callers */
export async function consumePendingBodyPhoto(): Promise<File | null> {
  const mem = getHandoffBodyPhoto()
  if (mem) return mem
  return restorePendingBodyPhotoFromStorage()
}
