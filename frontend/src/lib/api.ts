const USE_BFF = process.env.NEXT_PUBLIC_USE_BFF === '1'
const DIRECT_API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function generateUrl(): string {
  if (USE_BFF) {
    if (typeof window !== 'undefined') {
      return `${window.location.origin}/api/tattoo/generate`
    }
    return '/api/tattoo/generate'
  }
  return `${DIRECT_API}/api/generate`
}

function generateCoupleUrl(): string {
  if (USE_BFF) {
    if (typeof window !== 'undefined') {
      return `${window.location.origin}/api/tattoo/generate-couple`
    }
    return '/api/tattoo/generate-couple'
  }
  return `${DIRECT_API}/api/generate-couple`
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
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error((err as { detail?: string }).detail || `Error ${res.status}`)
    }

    return res.json() as Promise<GenerateResponse>
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
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error((err as { detail?: string }).detail || `Error ${res.status}`)
    }

    return res.json() as Promise<GenerateResponse>
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
