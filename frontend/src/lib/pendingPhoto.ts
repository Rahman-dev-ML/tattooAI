const KEY = 'tattoo-pending-body-photo'
const LOG = process.env.NODE_ENV === 'development'

function log(...args: unknown[]) {
  if (LOG) console.log('[pendingPhoto]', ...args)
}

export const FLOW_RESULT_KEY = (flowId: string) => `tattoo-result-${flowId}`

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
  if (typeof window === 'undefined') return false
  return sessionStorage.getItem(KEY) !== null
}

let storeInflight: Promise<void> | null = null
let storedFileKey: string | null = null

/** Compress + save to sessionStorage. Dedupes concurrent calls for the same file. */
export async function storePendingBodyPhoto(file: File): Promise<void> {
  const key = fileKey(file)
  if (storedFileKey === key && hasPendingBodyPhoto()) {
    log('already stored for', key)
    return
  }
  if (storeInflight && storedFileKey === key) {
    log('awaiting in-flight store for', key)
    return storeInflight
  }

  storedFileKey = key
  log('storing photo…', key, `${(file.size / 1024).toFixed(0)}KB`)

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
      log('stored OK', `${(dataUrl.length / 1024).toFixed(0)}KB in sessionStorage`)
    } catch (err) {
      storedFileKey = null
      console.error('[pendingPhoto] sessionStorage.setItem failed (quota?):', err)
      throw new Error('Photo too large to save. Try a smaller image or different photo.')
    }
  })().finally(() => {
    storeInflight = null
  })

  return storeInflight
}

export function clearPendingBodyPhoto(): void {
  if (typeof window === 'undefined') return
  sessionStorage.removeItem(KEY)
  storedFileKey = null
  log('cleared pending photo')
}

let consumeInflight: Promise<File | null> | null = null

/** Read pending homepage photo once. Removes from storage only after successful decode. */
export async function consumePendingBodyPhoto(): Promise<File | null> {
  if (typeof window === 'undefined') return null
  if (consumeInflight) return consumeInflight

  consumeInflight = (async () => {
    const raw = sessionStorage.getItem(KEY)
    if (!raw) {
      log('consume: nothing in sessionStorage')
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
      sessionStorage.removeItem(KEY)
      storedFileKey = null
      log('consume OK', name, `${(file.size / 1024).toFixed(0)}KB`)
      return file
    } catch (err) {
      console.error('[pendingPhoto] consume failed:', err)
      return null
    }
  })().finally(() => {
    consumeInflight = null
  })

  return consumeInflight
}
