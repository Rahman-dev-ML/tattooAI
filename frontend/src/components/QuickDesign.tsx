'use client'

import Link from 'next/link'
import { ArrowRight, Sparkles } from 'lucide-react'

export function QuickDesign() {
  return (
    <div className="min-h-screen bg-ink-950">
      <div className="w-full min-w-0 max-w-xl mx-auto px-4 py-10">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-ink-100/40 hover:text-ink-100/70 mb-8 transition"
        >
          ← Home
        </Link>

        <div className="mb-8">
          <h1 className="font-display text-3xl sm:text-4xl text-ink-100 mb-3 leading-tight">
            New to tattoos?
          </h1>
          <p className="text-ink-100/60 text-base">
            Upload a photo on the homepage, then answer 3 guided questions.
          </p>
        </div>

        <Link
          href="/flow/new_to_tattoos"
          className="group flex items-center gap-4 rounded-2xl border border-accent/40 bg-ink-900/60 p-5 transition active:scale-[0.99] hover:border-accent/60"
        >
          <div className="shrink-0 w-12 h-12 rounded-xl bg-accent/15 flex items-center justify-center">
            <Sparkles className="w-6 h-6 text-accent" />
          </div>
          <div className="flex-1 min-w-0">
            <span className="font-display text-base sm:text-lg text-ink-100 group-hover:text-accent transition leading-snug">
              Start guided tattoo preview
            </span>
            <p className="text-sm sm:text-base text-ink-100/55 leading-snug mt-1">
              3 quick questions — we handle the rest.
            </p>
          </div>
          <ArrowRight className="shrink-0 w-5 h-5 text-accent/60 group-hover:text-accent transition" />
        </Link>

        <p className="text-center text-xs text-ink-100/25 mt-10">
          Visual simulations only. Always consult a professional tattoo artist.
        </p>
      </div>
    </div>
  )
}
