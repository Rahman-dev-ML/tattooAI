import { NextRequest, NextResponse } from 'next/server'

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

  const deviceId = req.headers.get('X-Device-ID')
  if (deviceId) headers['X-Device-ID'] = deviceId

  const res = await fetch(`${backend.replace(/\/$/, '')}/api/generate-couple`, {
    method: 'POST',
    body: form,
    headers,
  })

  const text = await res.text()
  const responseHeaders: Record<string, string> = {
    'Content-Type': res.headers.get('Content-Type') || 'application/json',
  }
  const creditsHeader = res.headers.get('X-Credits-Remaining')
  if (creditsHeader !== null) responseHeaders['X-Credits-Remaining'] = creditsHeader

  return new NextResponse(text, { status: res.status, headers: responseHeaders })
}
