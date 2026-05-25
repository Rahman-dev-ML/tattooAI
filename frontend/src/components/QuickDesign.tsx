'use client'

import Link from 'next/link'
import {
  ArrowRight,
  Sparkles,
  Palette,
  Users,
  Shield,
  Camera,
  Clock,
  ChevronLeft,
} from 'lucide-react'

const FLOW_PATHS = [
  {
    id: 'new_to_tattoos',
    icon: Sparkles,
    title: 'I am new to tattoos',
    desc: 'Not sure where to start? 3 guided questions and we handle the rest.',
    badge: null,
    accentBg: false,
  },
  {
    id: 'from_idea',
    icon: Palette,
    title: 'I already have an idea',
    desc: 'Describe your concept and preferred style — see it on your body.',
    badge: null,
    accentBg: false,
  },
  {
    id: 'couple_tattoo',
    icon: Users,
    title: 'I want a couple tattoo',
    desc: 'Matching pair or two halves that connect when held together.',
    badge: null,
    accentBg: false,
  },
  {
    id: 'scar_coverup',
    icon: Shield,
    title: 'I want to cover or transform a scar',
    desc: 'Turn a scar, stretch mark, or old tattoo into something beautiful.',
    badge: 'Healing',
    accentBg: true,
  },
  {
    id: 'photo_convert',
    icon: Camera,
    title: 'I want to turn a photo into a tattoo',
    desc: 'Upload your pet, portrait, or sketch — we convert it to ink.',
    badge: null,
    accentBg: false,
  },
  {
    id: 'tattoo_fade',
    icon: Clock,
    title: 'I want to see how a tattoo may age',
    desc: 'Preview what a tattoo looks like after 2, 7, or 15 years of wear.',
    badge: null,
    accentBg: false,
  },
]

export function QuickDesign() {
  return (
    <div className="min-h-screen bg-ink-950">
      <div className="w-full min-w-0 max-w-xl mx-auto px-4 py-10">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-ink-100/40 hover:text-ink-100/70 mb-8 transition"
        >
          <ChevronLeft className="w-4 h-4" /> Home
        </Link>

        <div className="mb-8">
          <h1 className="font-display text-3xl sm:text-4xl text-ink-100 mb-3 leading-tight">
            What do you want to do?
          </h1>
          <p className="text-ink-100/60 text-base">
            Pick your path — each takes just 3 to 4 questions.
          </p>
        </div>

        <div className="space-y-3">
          {FLOW_PATHS.map((path) => (
            <Link
              key={path.id}
              href={`/flow/${path.id}`}
              className={`group flex items-center gap-4 rounded-2xl border p-5 transition active:scale-[0.99] ${
                path.accentBg
                  ? 'border-accent/40 bg-gradient-to-r from-accent/8 to-transparent hover:border-accent/60'
                  : 'border-border bg-ink-900/60 hover:border-accent/30 hover:bg-ink-900'
              }`}
            >
              <div
                className={`shrink-0 w-12 h-12 rounded-xl flex items-center justify-center ${
                  path.accentBg ? 'bg-accent/15' : 'bg-ink-800'
                }`}
              >
                <path.icon
                  className={`w-6 h-6 ${
                    path.accentBg ? 'text-accent' : 'text-accent/60 group-hover:text-accent transition'
                  }`}
                />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-display text-base sm:text-lg text-ink-100 group-hover:text-accent transition leading-snug">
                    {path.title}
                  </span>
                  {path.badge && (
                    <span className="shrink-0 text-[10px] font-bold tracking-wider uppercase text-accent bg-accent/15 px-2 py-0.5 rounded-full">
                      {path.badge}
                    </span>
                  )}
                </div>
                <p className="text-sm sm:text-base text-ink-100/55 leading-snug">{path.desc}</p>
              </div>

              <ArrowRight className="shrink-0 w-5 h-5 text-ink-100/20 group-hover:text-accent transition" />
            </Link>
          ))}
        </div>

        <p className="text-center text-xs text-ink-100/25 mt-10">
          Visual simulations only. Always consult a professional tattoo artist.
        </p>
      </div>
    </div>
  )
}
