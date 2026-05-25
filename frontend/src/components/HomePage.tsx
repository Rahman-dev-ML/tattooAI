'use client'

import Image from 'next/image'
import Link from 'next/link'
import { useEffect, useState } from 'react'
import {
  ArrowRight,
  CheckCircle2,
  Shield,
  Users,
  Camera,
  Sparkles,
  Upload,
  Wand2,
  Eye,
  Clock,
  Palette,
} from 'lucide-react'
import { HealingJourney } from './HealingJourney'
import { PageShell } from './PageShell'

function SplitCard({
  before,
  after,
  bodyPart,
  style,
  tag,
}: {
  before: string
  after: string
  bodyPart: string
  style: string
  tag?: string
}) {
  return (
    <div className="w-full min-w-0 rounded-2xl overflow-hidden border border-border bg-ink-900 flex flex-col">
      <div className="flex h-56 sm:h-64">
        <div className="relative w-1/2 bg-ink-950">
          <Image
            src={before}
            alt="Before"
            fill
            className="object-contain"
            sizes="(max-width:639px) 50vw, 220px"
          />
          <span className="absolute bottom-2 left-2 text-[10px] font-bold tracking-widest bg-ink-950/80 backdrop-blur-sm text-ink-100/65 px-2 py-1 rounded-lg">
            BEFORE
          </span>
        </div>

        <div className="relative shrink-0 w-px bg-ink-700">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-ink-900 border border-ink-600 flex items-center justify-center z-10 text-[9px] font-bold text-ink-100/30">
            ↔
          </div>
        </div>

        <div className="relative w-1/2 bg-ink-950">
          <Image
            src={after}
            alt="AI Preview"
            fill
            className="object-contain"
            sizes="(max-width:639px) 50vw, 220px"
          />
          {tag && (
            <span className="absolute top-2 left-2 text-[9px] font-bold tracking-widest bg-ink-950/75 text-accent px-1.5 py-0.5 rounded">
              {tag}
            </span>
          )}
          <span className="absolute bottom-2 right-2 text-[10px] font-bold tracking-widest bg-accent text-ink-950 px-2 py-1 rounded-lg">
            AI PREVIEW
          </span>
        </div>
      </div>

      <div className="px-4 py-3 border-t border-ink-800 flex items-center gap-2">
        <span className="text-xs font-semibold text-ink-100/75">{bodyPart}</span>
        <span className="text-ink-100/20 text-xs">·</span>
        <span className="text-xs text-ink-100/45">{style}</span>
      </div>
    </div>
  )
}

const PATHS = [
  { id: 'new_to_tattoos', icon: Sparkles, title: 'New to tattoos', sub: 'Guided discovery — 3 quick questions.', pill: null },
  { id: 'from_idea', icon: Palette, title: 'I have an idea', sub: 'Describe it, pick a style, see it on your skin.', pill: null },
  { id: 'couple_tattoo', icon: Users, title: 'Couple tattoo', sub: 'Matching pair or two halves of one design.', pill: null },
  { id: 'scar_coverup', icon: Shield, title: 'Cover up a scar', sub: 'Transform a scar into beautiful new art.', pill: 'Healing' },
  { id: 'photo_convert', icon: Camera, title: 'Photo to tattoo', sub: 'Upload any photo and convert it to ink.', pill: null },
  { id: 'tattoo_fade', icon: Clock, title: 'See how it ages', sub: 'Preview wear after 2 – 15 years.', pill: null },
]

const HOW = [
  { n: '1', icon: Upload, t: 'Upload or pick a body area', d: 'Take or upload a photo — or just pick a region if you prefer.' },
  { n: '2', icon: Wand2, t: 'Answer 3–4 short questions', d: 'Style, meaning, placement. No experience needed.' },
  { n: '3', icon: Eye, t: 'See the tattoo on your body', d: 'AI places a realistic preview on your photo. Save, compare, share.' },
]

export function HomePage() {
  const [paymentBanner, setPaymentBanner] = useState<{ credits: number } | null>(null)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const p = new URLSearchParams(window.location.search)
    if (p.get('payment') === 'success') {
      setPaymentBanner({ credits: parseInt(p.get('credits') || '5', 10) })
      window.history.replaceState({}, '', window.location.pathname)
      setTimeout(() => setPaymentBanner(null), 6000)
    }
  }, [])

  return (
    <PageShell className="min-h-screen bg-ink-950 text-ink-100">
      {paymentBanner && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 rounded-2xl border border-accent/30 bg-ink-900 px-5 py-3 shadow-2xl">
          <CheckCircle2 className="w-5 h-5 text-accent shrink-0" />
          <span className="text-sm font-medium">
            Payment successful — {paymentBanner.credits} credits added!
          </span>
        </div>
      )}

      <section className="w-full pt-10 pb-8 px-4 sm:px-5 text-center overflow-hidden">
        <div className="w-full max-w-2xl mx-auto">
          <span className="inline-block text-[11px] font-semibold tracking-widest uppercase text-accent mb-3">
            AI Tattoo Preview
          </span>
          <h1 className="font-display text-3xl sm:text-5xl font-semibold leading-tight mb-4">
            See your tattoo on your body
            <span className="text-accent"> before you commit.</span>
          </h1>
          <p className="text-ink-100/55 text-sm sm:text-base max-w-lg mx-auto mb-7 leading-relaxed">
            Upload a photo, answer 3 questions, and preview AI tattoo designs on your real skin before visiting an artist.
          </p>

          <div className="relative inline-flex py-3 px-3">
            <div
              className="absolute inset-0 rounded-full bg-accent/35 animate-ping pointer-events-none"
              style={{ animationDuration: '2s' }}
              aria-hidden
            />
            <Link
              href="/design"
              className="relative z-10 inline-flex items-center gap-2.5 rounded-full bg-accent px-8 py-4 text-ink-950 font-bold text-base hover:bg-accent/90 active:scale-[0.97] transition shadow-lg shadow-accent/30 animate-cta-pulse"
            >
              Start my tattoo preview
              <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
          <p className="mt-3 text-xs text-ink-100/30">Free to start · No sign-up needed</p>
        </div>
      </section>

      <section className="w-full px-4 sm:px-5 pb-10">
        <div className="w-full max-w-5xl mx-auto space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              { before: '/showcase/before-arm.jpeg', after: '/showcase/arm-after1.png', bodyPart: 'Male Forearm', style: 'Blackwork' },
              { before: '/showcase/before-arm.jpeg', after: '/showcase/arm-after2.png', bodyPart: 'Male Forearm', style: 'Japanese Color' },
              { before: '/showcase/sarah-before.jpg', after: '/showcase/sarah-after1.png', bodyPart: 'Female Forearm', style: 'Japanese' },
            ].map((c) => (
              <SplitCard key={c.style} {...c} />
            ))}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <SplitCard
              before="/showcase/scar1before.png"
              after="/showcase/scar1-after.jpeg"
              bodyPart="Forearm"
              style="Scar Cover-up"
              tag="SCAR"
            />

            <div className="w-full min-w-0 rounded-2xl overflow-hidden border border-border bg-ink-900 flex flex-col">
              <div className="relative h-56 sm:h-64 overflow-hidden">
                <Image
                  src="/showcase/cat-beforeafter.jpg"
                  alt="Photo to tattoo"
                  fill
                  className="object-cover object-center"
                  sizes="(max-width:639px) 100vw, 500px"
                />
                <div className="absolute inset-x-0 top-0 h-12 bg-gradient-to-b from-ink-950/70 to-transparent" />
                <span className="absolute top-3 left-3 text-[10px] font-bold tracking-widest bg-accent text-ink-950 px-2 py-1 rounded-lg">
                  PHOTO → AI TATTOO
                </span>
              </div>
              <div className="px-4 py-3 border-t border-ink-800 flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-semibold text-ink-100/75">Chest</span>
                  <span className="text-ink-100/20 text-xs">·</span>
                  <span className="text-xs text-ink-100/45">Photo to Tattoo · Blackwork</span>
                </div>
                <Link href="/flow/photo_convert" className="text-xs text-accent font-medium hover:underline flex items-center gap-1">
                  Try it <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="w-full bg-ink-900/50 px-4 sm:px-5 py-12">
        <div className="w-full max-w-5xl mx-auto">
          <p className="text-accent text-xs font-medium tracking-wider uppercase mb-2 text-center sm:text-left">
            Simple process
          </p>
          <h2 className="font-display text-2xl md:text-3xl text-ink-100 text-center sm:text-left mb-2">
            How it works
          </h2>
          <p className="text-sm text-ink-100/60 mb-8 text-center sm:text-left max-w-2xl">
            Upload a photo or pick a body area, answer a few questions, and see your design on skin.
          </p>
          <div className="grid sm:grid-cols-3 gap-8">
            {HOW.map((s) => (
              <div key={s.n} className="flex gap-4 sm:flex-col sm:gap-4">
                <div className="shrink-0 flex gap-3 items-center">
                  <span className="font-display text-4xl font-bold text-ink-100 leading-none">{s.n}</span>
                  <div className="w-11 h-11 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center">
                    <s.icon className="w-5 h-5 text-accent" />
                  </div>
                </div>
                <div>
                  <p className="font-display text-base sm:text-lg text-ink-100 mb-2">{s.t}</p>
                  <p className="text-sm text-ink-100/60 leading-relaxed">{s.d}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="paths" className="w-full px-4 sm:px-5 py-12">
        <div className="w-full max-w-5xl mx-auto">
          <p className="text-accent text-xs font-medium tracking-wider uppercase mb-2">Pick your flow</p>
          <h2 className="font-display text-2xl md:text-3xl text-ink-100 mb-2">Choose your path</h2>
          <p className="text-sm text-ink-100/60 mb-8 max-w-2xl">3–4 questions and you&apos;re generating.</p>
          <div className="space-y-3">
            {PATHS.map((p) => (
              <Link
                key={p.id}
                href={`/flow/${p.id}`}
                className={`group flex items-center gap-4 rounded-2xl border px-5 py-4 transition active:scale-[0.99] ${
                  p.id === 'scar_coverup'
                    ? 'border-accent/30 bg-ink-900 hover:border-accent/50'
                    : 'border-border bg-ink-900/50 hover:border-ink-100/15 hover:bg-ink-900'
                }`}
              >
                <div
                  className={`shrink-0 w-11 h-11 rounded-xl flex items-center justify-center ${
                    p.id === 'scar_coverup' ? 'bg-accent/10' : 'bg-ink-800'
                  }`}
                >
                  <p.icon
                    className={`w-5 h-5 ${
                      p.id === 'scar_coverup'
                        ? 'text-accent'
                        : 'text-ink-100/35 group-hover:text-accent/70 transition'
                    }`}
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-display text-base text-ink-100 group-hover:text-accent transition">{p.title}</span>
                    {p.pill && (
                      <span className="text-[10px] font-bold uppercase tracking-widest text-accent bg-accent/15 px-2 py-0.5 rounded-full">
                        {p.pill}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-ink-100/50 mt-1">{p.sub}</p>
                </div>
                <ArrowRight className="shrink-0 w-5 h-5 text-ink-100/15 group-hover:text-accent/60 transition" />
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="w-full bg-ink-900/40 px-4 sm:px-5 py-12">
        <div className="w-full max-w-5xl mx-auto">
          <p className="text-accent text-xs font-medium tracking-wider uppercase mb-2">Privacy &amp; safety</p>
          <h2 className="font-display text-2xl md:text-3xl text-ink-100 mb-2">Your data stays yours</h2>
          <p className="text-sm text-ink-100/60 mb-6 max-w-2xl">
            Previews are for planning only — always work with a licensed artist before getting inked.
          </p>
          <ul className="space-y-3">
            {[
              'Your photo is only used to create your preview',
              'Do not upload sensitive or private images',
              'AI previews are for planning only — not final designs',
              'Always consult a professional tattoo artist before getting inked',
              'Scar-related previews are not medical advice',
            ].map((t, i) => (
              <li key={i} className="flex items-start gap-3">
                <CheckCircle2 className="w-4 h-4 text-accent/45 shrink-0 mt-0.5" />
                <span className="text-sm text-ink-100/60 leading-relaxed">{t}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="w-full px-4 sm:px-5 py-14 text-center">
        <div className="w-full max-w-md mx-auto">
          <h2 className="font-display text-2xl mb-3">Ready to see it on your skin?</h2>
          <p className="text-ink-100/40 text-sm mb-7">No commitment. No artist visit yet.</p>
          <Link
            href="/design"
            className="inline-flex items-center gap-2 rounded-full bg-accent px-8 py-4 text-ink-950 font-bold hover:bg-accent/90 active:scale-[0.97] transition shadow-lg shadow-accent/20 animate-cta-pulse"
          >
            Start my preview <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      <div className="w-full max-w-5xl mx-auto px-4 sm:px-5">
        <HealingJourney />
      </div>

      <p className="w-full text-center text-[11px] text-ink-100/20 py-5 px-4 sm:px-5">
        Visual simulations only. Always consult a professional tattoo artist. Not medical advice.{' '}
        <Link href="/compare" className="text-accent/35 hover:underline">
          Compare tray →
        </Link>
      </p>
    </PageShell>
  )
}
