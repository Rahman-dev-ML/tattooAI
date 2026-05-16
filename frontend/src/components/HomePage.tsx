'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { ArrowRight, Heart, Sparkles, CheckCircle2 } from 'lucide-react'
import { HOME_FLOW_ORDER } from '@/lib/flowConfigs'
import { HealingJourney } from './HealingJourney'

const STRIP = [
  'Virtual body preview',
  'AI customized suggestions',
  'Fit score',
  'Faded tattoo simulation',
  'Save & compare',
]

export function HomePage() {
  const [paymentBanner, setPaymentBanner] = useState<{ credits: number } | null>(null)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    const status = params.get('payment')
    if (status === 'success') {
      const credits = parseInt(params.get('credits') || '5', 10)
      setPaymentBanner({ credits })
      window.history.replaceState({}, '', window.location.pathname)
      setTimeout(() => setPaymentBanner(null), 6000)
    }
  }, [])

  return (
    <div className="max-w-5xl mx-auto px-4 py-12 md:py-20">
      {paymentBanner && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 
                        rounded-2xl border border-accent/30 bg-ink-900 px-5 py-3 shadow-2xl">
          <CheckCircle2 className="w-5 h-5 text-accent shrink-0" />
          <span className="text-sm text-ink-100 font-medium">
            Payment successful — {paymentBanner.credits} credits added!
          </span>
        </div>
      )}
      <div className="text-center mb-14">
        <p className="text-accent text-sm font-medium tracking-wide uppercase mb-3">
          Tattoo Advisor
        </p>
        <h1 className="font-display text-4xl md:text-5xl lg:text-6xl font-semibold text-ink-100 leading-tight mb-4">
          See your tattoo on your body before you commit
        </h1>
        <p className="text-ink-100/70 text-lg max-w-2xl mx-auto mb-8">
          AI tattoo concepts with virtual body preview, fit guidance, and compare — planning
          support only, not medical advice.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            href="/flow/from_idea"
            className="inline-flex items-center justify-center gap-2 rounded-full bg-accent px-6 py-3 text-ink-950 font-medium hover:bg-accent/90 transition"
          >
            Start designing
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/flow/new_to_tattoos"
            className="inline-flex items-center justify-center gap-2 rounded-full border border-ink-100/20 px-6 py-3 text-ink-100 hover:bg-ink-800/50 transition"
          >
            New to tattoos
          </Link>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 gap-3 md:gap-4 mb-12">
        {HOME_FLOW_ORDER.map((f) => {
          const isScar = f.id === 'scar_coverup'
          return (
            <Link
              key={f.id}
              href={`/flow/${f.id}`}
              className={
                isScar
                  ? 'group rounded-2xl border border-accent/40 bg-gradient-to-br from-accent/10 to-ink-900/80 p-5 hover:border-accent/70 transition text-left relative overflow-hidden'
                  : 'group rounded-2xl border border-border bg-ink-900/80 p-5 hover:border-accent/40 transition text-left'
              }
            >
              {isScar && (
                <span className="absolute top-3 right-3 text-[10px] font-medium tracking-wider uppercase text-accent/90 bg-accent/15 px-2 py-0.5 rounded-full">
                  New
                </span>
              )}
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h2 className="font-display text-xl text-ink-100 mb-1 group-hover:text-accent transition">
                    {f.label}
                  </h2>
                  <p className="text-sm text-ink-100/55">{f.description}</p>
                </div>
                {isScar ? (
                  <Heart className="w-5 h-5 text-accent shrink-0 mt-1" />
                ) : (
                  <Sparkles className="w-5 h-5 text-accent/60 shrink-0 mt-1" />
                )}
              </div>
            </Link>
          )
        })}
        <div className="rounded-2xl border border-dashed border-border/80 bg-ink-900/40 p-5 flex flex-col justify-center">
          <p className="text-sm font-medium text-ink-100/50 mb-1">Roadmap</p>
          <p className="text-ink-100/40 text-sm">AR try-on</p>
        </div>
      </div>

      <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 text-xs text-ink-100/45 uppercase tracking-wider">
        {STRIP.map((s) => (
          <span key={s}>{s}</span>
        ))}
      </div>

      <HealingJourney />

      <p className="text-center text-xs text-ink-100/35 mt-10 max-w-xl mx-auto">
        Visual simulations only. Always consult a professional tattoo artist. Not medical advice.
      </p>

      <div className="text-center mt-6">
        <Link href="/compare" className="text-sm text-accent/90 hover:underline">
          Open compare tray →
        </Link>
      </div>
    </div>
  )
}
