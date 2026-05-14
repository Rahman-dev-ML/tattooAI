'use client'

import Link from 'next/link'
import { useState } from 'react'
import { CheckCircle2, Heart } from 'lucide-react'

export default function ShareStoryPage() {
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [form, setForm] = useState({
    name: '',
    age: '',
    scarType: '',
    strategy: '',
    quote: '',
    story: '',
    consent: false,
    anonymous: false,
  })
  const [photo, setPhoto] = useState<File | null>(null)

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((p) => ({ ...p, [key]: value }))
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!form.consent || !form.story.trim() || !form.quote.trim()) return
    setIsSubmitting(true)
    try {
      const payload = new FormData()
      payload.set('name', form.name)
      payload.set('age', form.age)
      payload.set('scarType', form.scarType)
      payload.set('strategy', form.strategy)
      payload.set('quote', form.quote)
      payload.set('story', form.story)
      payload.set('consent', String(form.consent))
      payload.set('anonymous', String(form.anonymous))
      if (photo) payload.set('photo', photo)

      const res = await fetch('/api/healing-stories', {
        method: 'POST',
        body: payload,
      })
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { error?: string }
        throw new Error(body.error || 'Could not submit your story.')
      }
      setSubmitted(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit your story.')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <div className="max-w-lg mx-auto px-4 py-16 text-center">
        <CheckCircle2 className="w-12 h-12 text-accent mx-auto mb-4" />
        <h1 className="font-display text-2xl text-ink-100 mb-2">
          Thank you for sharing
        </h1>
        <p className="text-ink-100/65 text-sm leading-relaxed mb-6">
          Your story will be reviewed by our small team and may be shared on the
          homepage to help others. We&apos;ll only publish what you consented to,
          and never your photo without explicit approval.
        </p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-ink-950"
        >
          Back to home
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-lg mx-auto px-4 py-10">
      <Link href="/" className="text-sm text-ink-100/50 hover:text-ink-100 mb-6 inline-block">
        ← Home
      </Link>
      <div className="flex items-center gap-2 mb-2">
        <Heart className="w-5 h-5 text-accent" />
        <p className="text-accent text-xs font-medium tracking-wider uppercase">
          Healing journey
        </p>
      </div>
      <h1 className="font-display text-3xl text-ink-100 mb-2">
        Share your story
      </h1>
      <p className="text-ink-100/60 text-sm mb-8">
        Your words might be exactly what someone scrolling at 2am needs to read.
        Anonymous welcome — share only what feels safe.
      </p>

      <form onSubmit={onSubmit} className="space-y-5">
        <div className="rounded-2xl border border-border bg-ink-900/60 p-5 space-y-4">
          <label className="block">
            <span className="text-sm text-ink-100">Name (or initials)</span>
            <input
              type="text"
              value={form.name}
              onChange={(e) => update('name', e.target.value)}
              placeholder="e.g. Maya, or M."
              disabled={form.anonymous}
              className="mt-1 w-full rounded-lg border border-border bg-ink-950 px-3 py-2 text-sm text-ink-100 disabled:opacity-50"
            />
          </label>

          <label className="flex items-center gap-2 text-sm text-ink-100/80">
            <input
              type="checkbox"
              checked={form.anonymous}
              onChange={(e) => update('anonymous', e.target.checked)}
              className="accent-accent"
            />
            Share anonymously
          </label>

          <label className="block">
            <span className="text-sm text-ink-100">Age (optional)</span>
            <input
              type="number"
              min={13}
              max={120}
              value={form.age}
              onChange={(e) => update('age', e.target.value)}
              className="mt-1 w-full rounded-lg border border-border bg-ink-950 px-3 py-2 text-sm text-ink-100"
            />
          </label>

          <label className="block">
            <span className="text-sm text-ink-100">Scar type</span>
            <select
              value={form.scarType}
              onChange={(e) => update('scarType', e.target.value)}
              className="mt-1 w-full rounded-lg border border-border bg-ink-950 px-3 py-2 text-sm text-ink-100"
            >
              <option value="">Choose…</option>
              <option value="Surgical">Surgical / incision</option>
              <option value="Injury">Injury / accident</option>
              <option value="Burn">Burn</option>
              <option value="Stretch marks">Stretch marks</option>
              <option value="C-section">C-section</option>
              <option value="Mastectomy">Mastectomy</option>
              <option value="Healing journey">Healing journey</option>
              <option value="Other">Other</option>
            </select>
          </label>

          <label className="block">
            <span className="text-sm text-ink-100">Strategy you chose</span>
            <select
              value={form.strategy}
              onChange={(e) => update('strategy', e.target.value)}
              className="mt-1 w-full rounded-lg border border-border bg-ink-950 px-3 py-2 text-sm text-ink-100"
            >
              <option value="">Choose…</option>
              <option value="Camouflage">Camouflage</option>
              <option value="Transform">Transform</option>
              <option value="Overshadow">Overshadow</option>
            </select>
          </label>
        </div>

        <div className="rounded-2xl border border-border bg-ink-900/60 p-5 space-y-4">
          <label className="block">
            <span className="text-sm text-ink-100">A line that captures it</span>
            <input
              type="text"
              required
              value={form.quote}
              onChange={(e) => update('quote', e.target.value)}
              placeholder="One sentence — your headline."
              maxLength={160}
              className="mt-1 w-full rounded-lg border border-border bg-ink-950 px-3 py-2 text-sm text-ink-100"
            />
            <span className="text-[11px] text-ink-100/45 mt-1 block">
              {form.quote.length}/160
            </span>
          </label>

          <label className="block">
            <span className="text-sm text-ink-100">Your story</span>
            <textarea
              required
              value={form.story}
              onChange={(e) => update('story', e.target.value)}
              rows={6}
              placeholder="What happened, what you tried, how the design felt the first time you saw it…"
              maxLength={1200}
              className="mt-1 w-full rounded-lg border border-border bg-ink-950 px-3 py-2 text-sm text-ink-100"
            />
            <span className="text-[11px] text-ink-100/45 mt-1 block">
              {form.story.length}/1200
            </span>
          </label>
        </div>

        <div className="rounded-2xl border border-border bg-ink-900/60 p-5 space-y-3">
          <label className="block">
            <span className="text-sm text-ink-100">Optional photo</span>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(e) => setPhoto(e.target.files?.[0] || null)}
              className="mt-1 w-full rounded-lg border border-border bg-ink-950 px-3 py-2 text-sm text-ink-100 file:mr-3 file:rounded-full file:border-0 file:bg-accent/20 file:px-3 file:py-1 file:text-accent"
            />
          </label>
          <p className="text-xs text-ink-100/55">
            Photo is optional and will stay in moderation review until approved.
          </p>
        </div>

        <label className="flex items-start gap-2 text-sm text-ink-100/80">
          <input
            type="checkbox"
            required
            checked={form.consent}
            onChange={(e) => update('consent', e.target.checked)}
            className="accent-accent mt-1"
          />
          <span>
            I consent to my story being reviewed and possibly published on the
            homepage. I will not include private information (full name, exact
            location, etc.). I can withdraw at any time.
          </span>
        </label>

        <button
          type="submit"
          disabled={!form.consent || !form.story.trim() || !form.quote.trim() || isSubmitting}
          className="inline-flex items-center justify-center gap-2 rounded-full bg-accent px-6 py-3 text-sm font-medium text-ink-950 disabled:opacity-40 w-full sm:w-auto"
        >
          {isSubmitting ? 'Submitting...' : 'Submit story'}
        </button>
        {error && <p className="text-xs text-red-300">{error}</p>}

        <p className="text-xs text-ink-100/45">
          Submissions route to a moderated review queue. Nothing is published
          without a human review.
        </p>
      </form>
    </div>
  )
}
