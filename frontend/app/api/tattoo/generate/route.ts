import { NextRequest, NextResponse } from 'next/server'

/**
 * Server-side proxy: browser never sees TATTOO_SERVICE_KEY.
 * Set TATTOO_BACKEND_URL (e.g. http://127.0.0.1:8000) and optional TATTOO_SERVICE_KEY.
 * Enable from the client with NEXT_PUBLIC_USE_BFF=1.
 */
export async function POST(req: NextRequest) {
  const backend = process.env.TATTOO_BACKEND_URL
  if (!backend) {
    return NextResponse.json(
      { detail: 'Set TATTOO_BACKEND_URL in the Next.js server environment to use the BFF proxy.' },
      { status: 501 }
    )
  }

  const form = await req.formData()
  const key = process.env.TATTOO_SERVICE_KEY
  const headers: Record<string, string> = {}
  if (key) headers['X-API-Key'] = key

  const res = await fetch(`${backend.replace(/\/$/, '')}/api/generate`, {
    method: 'POST',
    body: form,
    headers,
  })

  const text = await res.text()
  return new NextResponse(text, {
    status: res.status,
    headers: { 'Content-Type': res.headers.get('Content-Type') || 'application/json' },
  })
}
