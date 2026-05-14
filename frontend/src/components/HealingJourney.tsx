'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { ArrowRight, Heart, Quote } from 'lucide-react'
import { FALLBACK_HEALING_STORIES, type HealingStory } from '@/lib/healingStories'

export function HealingJourney() {
  const [open, setOpen] = useState<HealingStory | null>(null)
  const [stories, setStories] = useState<HealingStory[]>(FALLBACK_HEALING_STORIES)

  useEffect(() => {
    let active = true
    async function loadStories() {
      try {
        const res = await fetch('/api/healing-stories', { cache: 'no-store' })
        if (!res.ok) return
        const body = (await res.json()) as { stories?: HealingStory[] }
        if (!active || !Array.isArray(body.stories) || body.stories.length === 0) return
        setStories(body.stories)
      } catch {
        // keep fallback stories silently
      }
    }
    loadStories()
    return () => {
      active = false
    }
  }, [])

  return (
    <section className="mt-16 mb-12">
      <div className="flex items-end justify-between gap-4 mb-6">
        <div>
          <p className="text-accent text-xs font-medium tracking-wider uppercase mb-2">
            Healing journeys
          </p>
          <h2 className="font-display text-2xl md:text-3xl text-ink-100">
            Real people, real transformations
          </h2>
          <p className="text-sm text-ink-100/60 mt-1 max-w-2xl">
            Stories from people who turned their scars into art. Names &amp;
            details shared with permission. Submit yours below.
          </p>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        {stories.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setOpen(s)}
            className="text-left rounded-2xl border border-border bg-ink-900/70 p-4 hover:border-accent/50 transition group"
          >
            {s.photoUrl && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={s.photoUrl}
                alt={`${s.name} story photo`}
                className="w-full h-28 rounded-xl object-cover mb-3 border border-border/80"
              />
            )}
            <div className="flex items-center gap-2 mb-3">
              <span className="grid place-items-center w-8 h-8 rounded-full bg-accent/15 text-accent text-sm font-semibold">
                {s.initial}
              </span>
              <div className="min-w-0">
                <p className="text-sm text-ink-100 truncate">
                  {s.name}
                  {s.age != null && (
                    <span className="text-ink-100/45">, {s.age}</span>
                  )}
                </p>
                <p className="text-[11px] text-ink-100/50 truncate">
                  {s.scarType} · {s.strategy}
                </p>
              </div>
            </div>
            <Quote className="w-4 h-4 text-accent/40 mb-1" />
            <p className="text-sm text-ink-100/80 leading-relaxed line-clamp-4">
              {s.quote}
            </p>
            <p className="text-xs text-accent/80 mt-3 inline-flex items-center gap-1 group-hover:gap-1.5 transition-all">
              Read story <ArrowRight className="w-3 h-3" />
            </p>
          </button>
        ))}
      </div>

      <div className="mt-6 rounded-2xl border border-dashed border-accent/30 bg-accent/5 p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3 min-w-0">
          <Heart className="w-5 h-5 text-accent shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-ink-100">
              Share your story (with permission)
            </p>
            <p className="text-xs text-ink-100/60 mt-0.5">
              Help someone who&apos;s where you used to be. Anonymous welcome.
            </p>
          </div>
        </div>
        <Link
          href="/share-story"
          className="inline-flex items-center gap-1.5 rounded-full bg-accent px-4 py-2 text-sm font-medium text-ink-950 hover:bg-accent/90 shrink-0"
        >
          Submit story <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {open && (
        <div
          className="fixed inset-0 z-50 bg-black/70 flex items-end sm:items-center justify-center p-4"
          onClick={() => setOpen(null)}
        >
          <div
            className="relative max-w-lg w-full rounded-2xl border border-border bg-ink-900 p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              onClick={() => setOpen(null)}
              className="absolute top-3 right-3 text-ink-100/50 hover:text-ink-100 text-sm"
              aria-label="Close"
            >
              ✕
            </button>
            <div className="flex items-center gap-3 mb-4">
              <span className="grid place-items-center w-12 h-12 rounded-full bg-accent/15 text-accent text-lg font-semibold">
                {open.initial}
              </span>
              <div>
                <p className="text-base text-ink-100">
                  {open.name}
                  {open.age != null && (
                    <span className="text-ink-100/50"> · {open.age}</span>
                  )}
                </p>
                <p className="text-xs text-ink-100/55">
                  {open.scarType} · {open.strategy} strategy
                </p>
              </div>
            </div>
            <Quote className="w-5 h-5 text-accent/60 mb-2" />
            <p className="text-base text-ink-100 leading-relaxed mb-4 italic">
              “{open.quote}”
            </p>
            {open.photoUrl && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={open.photoUrl}
                alt={`${open.name} journey photo`}
                className="w-full rounded-xl object-cover max-h-72 mb-4 border border-border/80"
              />
            )}
            <p className="text-sm text-ink-100/75 leading-relaxed">
              {open.story}
            </p>
          </div>
        </div>
      )}
    </section>
  )
}
