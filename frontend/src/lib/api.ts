const DIRECT_API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const DEVICE_KEY = 'tattoo-device-id'
const FP_INITIALIZED_KEY = 'tattoo-fp-init'

export interface PaymentSessionResponse {
  checkout_url: string
  form_data: Record<string, string>
  basket_id: string
}

/**
 * Synchronous: reads cached device ID from localStorage.
 * Falls back to a random UUID on very first visit (before FP loads).
 */
export function getDeviceId(): string {
  if (typeof window === 'undefined') return 'ssr'
  let id = localStorage.getItem(DEVICE_KEY)
  if (!id) {
    id = crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`
    localStorage.setItem(DEVICE_KEY, id)
  }
  return id
}

/**
 * Async: generates a stable FingerprintJS fingerprint and overwrites the
 * localStorage device ID with it. Called once on app load.
 * After this, getDeviceId() returns the fingerprint-based ID — survives
 * localStorage clears because the same fingerprint is regenerated from
 * browser hardware/software attributes.
 */
export async function initDeviceId(): Promise<string> {
  if (typeof window === 'undefined') return 'ssr'

  // Only regenerate if not already set via FP (avoid re-importing every render)
  if (localStorage.getItem(FP_INITIALIZED_KEY) === '1') {
    return getDeviceId()
  }

  try {
    const FingerprintJS = (await import('@fingerprintjs/fingerprintjs')).default
    const fp = await FingerprintJS.load()
    const result = await fp.get()
    const fpId = `fp-${result.visitorId}`
    localStorage.setItem(DEVICE_KEY, fpId)
    localStorage.setItem(FP_INITIALIZED_KEY, '1')
    return fpId
  } catch {
    // FP failed (ad blocker, private mode restriction) — keep UUID fallback
    localStorage.setItem(FP_INITIALIZED_KEY, '1')
    return getDeviceId()
  }
}

export async function checkCredits(): Promise<number> {
  try {
    const res = await fetch(`${DIRECT_API}/api/credits`, {
      headers: { 'X-Device-ID': getDeviceId() },
      signal: AbortSignal.timeout(5000),
    })
    if (!res.ok) return 2
    const data = await res.json()
    return data.credits ?? 2
  } catch {
    return 2
  }
}

export async function initiatePayment(): Promise<PaymentSessionResponse> {
  const res = await fetch(`${DIRECT_API}/api/payment/initiate`, {
    method: 'POST',
    headers: { 'X-Device-ID': getDeviceId() },
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'Payment initiation failed')
  return data
}

export function redirectToPayFast(checkoutUrl: string, formData: Record<string, string>) {
  const form = document.createElement('form')
  form.method = 'POST'
  form.action = checkoutUrl
  form.style.display = 'none'
  for (const [key, value] of Object.entries(formData)) {
    const input = document.createElement('input')
    input.type = 'hidden'
    input.name = key
    input.value = value
    form.appendChild(input)
  }
  document.body.appendChild(form)
  form.submit()
}

function generateUrl(): string {
  if (typeof window !== 'undefined') {
    return `${window.location.origin}/api/tattoo/generate`
  }
  return '/api/tattoo/generate'
}

function generateCoupleUrl(): string {
  if (typeof window !== 'undefined') {
    return `${window.location.origin}/api/tattoo/generate-couple`
  }
  return '/api/tattoo/generate-couple'
}

const GENERATION_TIMEOUT_MS = 240_000

import type { FlowAnswers, FlowId, GenerateResponse } from './types'

export async function generateTattoos(
  image: File,
  flowId: FlowId,
  answers: FlowAnswers,
  numConcepts = 1,
  referenceImage?: File | null
): Promise<GenerateResponse> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), GENERATION_TIMEOUT_MS)

  const form = new FormData()
  form.append('image', image)
  form.append('flow_id', flowId)
  form.append('answers_json', JSON.stringify(answers))
  form.append('num_concepts', String(numConcepts))
  if (referenceImage) {
    form.append('reference_image', referenceImage)
  }

  try {
    const res = await fetch(generateUrl(), {
      method: 'POST',
      body: form,
      signal: controller.signal,
      headers: { 'X-Device-ID': getDeviceId() },
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      const e = new Error((err as { detail?: string }).detail || `Error ${res.status}`)
      ;(e as any).status = res.status
      throw e
    }

    const data = await res.json() as GenerateResponse
    const creditsHeader = res.headers.get('X-Credits-Remaining')
    if (creditsHeader !== null) (data as any).creditsRemaining = parseInt(creditsHeader, 10)
    return data
  } finally {
    clearTimeout(timeoutId)
  }
}

export async function generateCoupleTattoos(
  imageA: File | null,
  imageB: File | null,
  answers: FlowAnswers
): Promise<GenerateResponse> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), GENERATION_TIMEOUT_MS)

  const form = new FormData()
  // complementary_split mode is photoless on the backend — only matching_pair
  // requires the two partner photos.
  if (imageA) form.append('image_a', imageA)
  if (imageB) form.append('image_b', imageB)
  form.append('answers_json', JSON.stringify(answers))

  try {
    const res = await fetch(generateCoupleUrl(), {
      method: 'POST',
      body: form,
      signal: controller.signal,
      headers: { 'X-Device-ID': getDeviceId() },
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      const e = new Error((err as { detail?: string }).detail || `Error ${res.status}`)
      ;(e as any).status = res.status
      throw e
    }

    const data = await res.json() as GenerateResponse
    const creditsHeader = res.headers.get('X-Credits-Remaining')
    if (creditsHeader !== null) (data as any).creditsRemaining = parseInt(creditsHeader, 10)
    return data
  } finally {
    clearTimeout(timeoutId)
  }
}

export async function checkAiStatus(): Promise<boolean> {
  try {
    const res = await fetch(`${DIRECT_API}/api/ai-status`, { signal: AbortSignal.timeout(5000) })
    const data = await res.json()
    return Boolean(data.ai_available)
  } catch {
    return false
  }
}
