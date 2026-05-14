import { NextResponse } from 'next/server'
import { FALLBACK_HEALING_STORIES, type HealingStory, type HealingStrategy } from '@/lib/healingStories'

type StoryRecord = {
  id: string
  display_name: string | null
  age: number | null
  scar_type: string | null
  strategy: HealingStrategy | null
  quote: string | null
  story: string | null
  is_anonymous: boolean | null
  photo_url: string | null
}

const MAX_IMAGE_BYTES = 8 * 1024 * 1024
const IMAGE_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp'])
const MIN_VISIBLE_STORIES = 3

function getSupabaseConfig() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL || ''
  const key =
    process.env.SUPABASE_SERVICE_ROLE_KEY ||
    process.env.SUPABASE_ANON_KEY ||
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
    ''
  return { url: url.replace(/\/+$/, ''), key }
}

function normalizeStory(row: StoryRecord): HealingStory {
  const name =
    row.is_anonymous || !row.display_name?.trim() ? 'Anonymous' : row.display_name.trim()
  return {
    id: row.id,
    initial: name.charAt(0).toUpperCase() || 'A',
    name,
    age: row.age ?? undefined,
    scarType: row.scar_type?.trim() || 'Healing journey',
    strategy: (row.strategy as HealingStrategy) || 'Transform',
    quote: row.quote?.trim() || '',
    story: row.story?.trim() || '',
    photoUrl: row.photo_url || null,
  }
}

async function uploadPhotoToSupabase(
  file: File,
  supabaseUrl: string,
  supabaseKey: string
): Promise<string> {
  const ext = file.name.includes('.') ? file.name.split('.').pop()?.toLowerCase() : 'jpg'
  const safeExt = ext && /^[a-z0-9]+$/.test(ext) ? ext : 'jpg'
  const objectPath = `submissions/${crypto.randomUUID()}.${safeExt}`
  const uploadUrl = `${supabaseUrl}/storage/v1/object/healing-journeys/${objectPath}`
  const uploadRes = await fetch(uploadUrl, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${supabaseKey}`,
      apikey: supabaseKey,
      'Content-Type': file.type || 'application/octet-stream',
      'x-upsert': 'false',
    },
    body: file,
  })
  if (!uploadRes.ok) {
    const text = await uploadRes.text()
    throw new Error(`Photo upload failed: ${uploadRes.status} ${text.slice(0, 180)}`)
  }
  return `${supabaseUrl}/storage/v1/object/public/healing-journeys/${objectPath}`
}

export async function GET() {
  const { url, key } = getSupabaseConfig()
  if (!url || !key) {
    return NextResponse.json({ stories: FALLBACK_HEALING_STORIES, source: 'fallback' })
  }
  try {
    const res = await fetch(
      `${url}/rest/v1/healing_stories?select=id,display_name,age,scar_type,strategy,quote,story,is_anonymous,photo_url&status=neq.rejected&order=created_at.desc&limit=24`,
      {
        headers: {
          Authorization: `Bearer ${key}`,
          apikey: key,
        },
        cache: 'no-store',
      }
    )
    if (!res.ok) {
      const text = await res.text()
      throw new Error(`Fetch failed: ${res.status} ${text.slice(0, 180)}`)
    }
    const rows = (await res.json()) as StoryRecord[]
    const stories = rows
      .map(normalizeStory)
      .filter((s) => s.quote.trim().length > 0 && s.story.trim().length > 0)
    const realStories = stories.slice(0, 24)
    const placeholdersNeeded = Math.max(0, MIN_VISIBLE_STORIES - realStories.length)
    const placeholderStories = FALLBACK_HEALING_STORIES.filter(
      (fb) => !realStories.some((story) => story.id === fb.id)
    ).slice(0, placeholdersNeeded)
    const mergedStories = [...realStories, ...placeholderStories]
    return NextResponse.json({
      stories: mergedStories.length > 0 ? mergedStories : FALLBACK_HEALING_STORIES,
      source:
        realStories.length > 0 && placeholderStories.length > 0
          ? 'supabase+fallback'
          : realStories.length > 0
          ? 'supabase'
          : 'fallback',
    })
  } catch {
    return NextResponse.json({ stories: FALLBACK_HEALING_STORIES, source: 'fallback' })
  }
}

export async function POST(req: Request) {
  const { url, key } = getSupabaseConfig()
  if (!url || !key) {
    return NextResponse.json(
      { error: 'Supabase is not configured on server environment.' },
      { status: 500 }
    )
  }

  try {
    const form = await req.formData()
    const quote = String(form.get('quote') || '').trim()
    const story = String(form.get('story') || '').trim()
    const scarType = String(form.get('scarType') || '').trim()
    const strategyRaw = String(form.get('strategy') || '').trim()
    const displayName = String(form.get('name') || '').trim()
    const ageRaw = String(form.get('age') || '').trim()
    const consentRaw = String(form.get('consent') || '').toLowerCase()
    const anonymousRaw = String(form.get('anonymous') || '').toLowerCase()
    const photo = form.get('photo')

    if (!quote || !story) {
      return NextResponse.json({ error: 'Quote and story are required.' }, { status: 400 })
    }
    if (quote.length > 160 || story.length > 1200) {
      return NextResponse.json({ error: 'Story exceeds allowed length.' }, { status: 400 })
    }
    const consent =
      consentRaw === 'true' || consentRaw === '1' || consentRaw === 'on' || consentRaw === 'yes'
    if (!consent) {
      return NextResponse.json({ error: 'Consent is required.' }, { status: 400 })
    }
    const isAnonymous =
      anonymousRaw === 'true' ||
      anonymousRaw === '1' ||
      anonymousRaw === 'on' ||
      anonymousRaw === 'yes'
    const strategy: HealingStrategy =
      strategyRaw === 'Camouflage' || strategyRaw === 'Transform' || strategyRaw === 'Overshadow'
        ? strategyRaw
        : 'Transform'
    const ageNum = ageRaw ? Number(ageRaw) : null
    const age = Number.isFinite(ageNum) && ageNum && ageNum >= 13 && ageNum <= 120 ? ageNum : null

    let photoUrl: string | null = null
    if (photo instanceof File && photo.size > 0) {
      if (!IMAGE_TYPES.has(photo.type)) {
        return NextResponse.json(
          { error: 'Photo must be JPG, PNG, or WEBP.' },
          { status: 400 }
        )
      }
      if (photo.size > MAX_IMAGE_BYTES) {
        return NextResponse.json(
          { error: 'Photo size exceeds 8MB limit.' },
          { status: 400 }
        )
      }
      photoUrl = await uploadPhotoToSupabase(photo, url, key)
    }

    const payload = {
      display_name: isAnonymous ? null : displayName || null,
      age,
      scar_type: scarType || null,
      strategy,
      quote,
      story,
      consent,
      is_anonymous: isAnonymous,
      photo_url: photoUrl,
      status: 'pending',
    }

    const insertRes = await fetch(`${url}/rest/v1/healing_stories`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${key}`,
        apikey: key,
        'Content-Type': 'application/json',
        Prefer: 'return=representation',
      },
      body: JSON.stringify(payload),
    })
    if (!insertRes.ok) {
      const text = await insertRes.text()
      return NextResponse.json(
        { error: `Save failed: ${insertRes.status} ${text.slice(0, 180)}` },
        { status: 500 }
      )
    }
    return NextResponse.json({ ok: true })
  } catch {
    return NextResponse.json({ error: 'Could not submit story.' }, { status: 500 })
  }
}

