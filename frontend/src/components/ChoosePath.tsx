'use client'

import Link from 'next/link'
import {
  ArrowRight,
  Camera,
  Clock,
  Palette,
  Shield,
  Sparkles,
  Users,
} from 'lucide-react'
import type { FlowId } from '@/lib/types'

const PATHS: {
  id: FlowId
  label: string
  description: string
  icon: typeof Sparkles
  badge?: string
  featured?: boolean
}[] = [
  {
    id: 'new_to_tattoos',
    label: 'New to tattoos',
    description: 'Guided discovery — 3 quick questions.',
    icon: Sparkles,
  },
  {
    id: 'from_idea',
    label: 'I have an idea',
    description: 'Describe it, pick a style, see it on your skin.',
    icon: Palette,
  },
  {
    id: 'couple_tattoo',
    label: 'Couple tattoo',
    description: 'Matching pair or two halves of one design.',
    icon: Users,
  },
  {
    id: 'scar_coverup',
    label: 'Cover up a scar',
    description: 'Transform a scar into beautiful new art.',
    icon: Shield,
    badge: 'Healing',
    featured: true,
  },
  {
    id: 'photo_convert',
    label: 'Photo to tattoo',
    description: 'Upload any photo and convert it to ink.',
    icon: Camera,
  },
  {
    id: 'tattoo_fade',
    label: 'See how it ages',
    description: 'Preview wear after 2 – 15 years.',
    icon: Clock,
  },
]

export function ChoosePath() {
  return (
    <section className="mb-16">
      <p className="text-accent text-xs font-semibold tracking-[0.2em] uppercase mb-3">
        Pick your flow
      </p>
      <h2 className="font-display text-3xl md:text-4xl text-ink-100 mb-2">Choose your path</h2>
      <p className="text-ink-100/55 text-sm mb-8">3–4 questions and you&apos;re generating.</p>

      <div className="space-y-3">
        {PATHS.map((path) => {
          const Icon = path.icon
          return (
            <Link
              key={path.id}
              href={`/flow/${path.id}`}
              className={
                path.featured
                  ? 'group flex items-center gap-4 rounded-2xl border border-accent/50 bg-gradient-to-r from-accent/[0.08] to-ink-900/80 px-4 py-4 hover:border-accent/70 transition'
                  : 'group flex items-center gap-4 rounded-2xl border border-border/80 bg-ink-900/40 px-4 py-4 hover:border-ink-100/20 hover:bg-ink-900/70 transition'
              }
            >
              <div
                className={
                  path.featured
                    ? 'shrink-0 w-11 h-11 rounded-xl bg-accent/15 border border-accent/30 flex items-center justify-center'
                    : 'shrink-0 w-11 h-11 rounded-xl bg-ink-800/80 border border-border flex items-center justify-center'
                }
              >
                <Icon
                  className={
                    path.featured ? 'w-5 h-5 text-accent' : 'w-5 h-5 text-ink-100/45 group-hover:text-ink-100/70'
                  }
                />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3
                    className={
                      path.featured
                        ? 'text-base font-semibold text-ink-100'
                        : 'text-base font-medium text-ink-100 group-hover:text-accent transition'
                    }
                  >
                    {path.label}
                  </h3>
                  {path.badge && (
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-accent text-ink-950">
                      {path.badge}
                    </span>
                  )}
                </div>
                <p className="text-sm text-ink-100/45 mt-0.5">{path.description}</p>
              </div>
              <ArrowRight
                className={
                  path.featured
                    ? 'w-4 h-4 text-accent/70 shrink-0'
                    : 'w-4 h-4 text-ink-100/25 shrink-0 group-hover:text-ink-100/50 transition'
                }
              />
            </Link>
          )
        })}
      </div>
    </section>
  )
}
