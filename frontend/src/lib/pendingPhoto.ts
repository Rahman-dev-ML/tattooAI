const KEY = 'tattoo-pending-body-photo'

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

export async function storePendingBodyPhoto(file: File): Promise<void> {
  const dataUrl = await fileToDataUrl(file)
  sessionStorage.setItem(
    KEY,
    JSON.stringify({
      dataUrl,
      name: file.name,
      type: file.type,
      lastModified: file.lastModified,
    })
  )
}

export async function consumePendingBodyPhoto(): Promise<File | null> {
  if (typeof window === 'undefined') return null
  const raw = sessionStorage.getItem(KEY)
  if (!raw) return null
  sessionStorage.removeItem(KEY)
  try {
    const { dataUrl, name, type, lastModified } = JSON.parse(raw) as {
      dataUrl: string
      name: string
      type: string
      lastModified: number
    }
    const res = await fetch(dataUrl)
    const blob = await res.blob()
    return new File([blob], name, { type, lastModified })
  } catch {
    return null
  }
}
