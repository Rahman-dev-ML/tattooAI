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
  { id: 'scar_coverup', icon: Shield, title: 'Cover up a scar', sub: 'Transform a scar into beautiful new art.', pill: 'Healing' },
  { id: 'tattoo_fade', icon: Clock, title: 'See how it ages', sub: 'Preview natural fade after 10–15 years.', pill: null },
  { id: 'from_idea', icon: Palette, title: 'I have an idea', sub: 'Describe it, pick a style, see it on your skin.', pill: null },
  { id: 'couple_tattoo', icon: Users, title: 'Couple tattoo', sub: 'Matching pair or two halves of one design.', pill: null },
  { id: 'photo_convert', icon: Camera, title: 'Photo to tattoo', sub: 'Upload any photo and convert it to ink.', pill: null },
]

const HOW = [
  { n: '1', icon: Upload, t: 'Upload or pick a body area', d: 'Take or upload a photo — or just pick a region if you prefer.' },
  { n: '2', icon: Wand2, t: 'Answer 3–4 short questions', d: 'Style, meaning, placement. No experience needed.' },
  { n: '3', icon: Eye, t: 'See the tattoo on your body', d: 'AI places a realistic preview on your photo. Save, compare, share.' },
]

const FADED_BEFORE = '/showcase/FADEDTRY3.png'
const FADED_AFTER = '/showcase/faded-after.jpeg'

const TRUST = [
  { icon: Shield, t: 'Private & secure', d: 'Photos used only for your preview' },
  { icon: Sparkles, t: 'No sign-up', d: 'Start instantly — no account' },
  { icon: Eye, t: 'Real previews', d: 'See ink on your own skin' },
  { icon: Clock, t: 'Under 5 minutes', d: 'From upload to design' },
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
          <span className="inline-flex items-center gap-1.5 rounded-full border border-accent/40 bg-accent/10 px-3 py-1.5 text-[11px] sm:text-xs font-bold tracking-wide text-accent mb-4">
            <Sparkles className="w-3.5 h-3.5" /> 2 FREE PREVIEWS · NO CARD NEEDED
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
          <p className="mt-3 text-xs sm:text-sm text-ink-100/50">
            <span className="text-accent font-semibold">2 previews free</span> — no sign-up, no card. Then 5 more for just <span className="text-ink-100/80 font-semibold">$1</span>.
          </p>
        </div>
      </section>

      <section className="w-full px-4 sm:px-5 pb-8">
        <div className="w-full max-w-5xl mx-auto grid grid-cols-2 sm:grid-cols-4 gap-3">
          {TRUST.map((b) => (
            <div
              key={b.t}
              className="rounded-2xl border border-border bg-ink-900/60 px-4 py-3.5 flex flex-col gap-1"
            >
              <div className="flex items-center gap-2">
                <b.icon className="w-4 h-4 text-accent shrink-0" />
                <span className="text-xs sm:text-sm font-semibold text-ink-100/85">{b.t}</span>
              </div>
              <span className="text-[11px] sm:text-xs text-ink-100/45 leading-snug">{b.d}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="w-full px-4 sm:px-5 pb-10">
        <div className="w-full max-w-5xl mx-auto">
          <div className="text-center mb-6">
            <p className="text-accent text-xs font-medium tracking-wider uppercase mb-2">Real before &amp; after</p>
            <h2 className="font-display text-2xl md:text-3xl text-ink-100">What others describe, we show you</h2>
            <p className="text-sm text-ink-100/55 mt-2 max-w-xl mx-auto">
              Cover a scar, age a tattoo 10–15 years, or turn a photo into ink — the features that set us apart, shown on real skin.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <SplitCard
              before="/showcase/scar1before.png"
              after="/showcase/scar1-after.jpeg"
              bodyPart="Forearm"
              style="Scar Cover-up"
              tag="SCAR"
            />
            <SplitCard
              before={FADED_BEFORE}
              after={FADED_AFTER}
              bodyPart="Forearm"
              style="Aged 10–15 yrs"
              tag="10–15 YRS"
            />

            <div className="w-full min-w-0 rounded-2xl overflow-hidden border border-border bg-ink-900 flex flex-col">
              <div className="relative h-56 sm:h-64 overflow-hidden">
                <Image
                  src="/showcase/cat-beforeafter.jpg"
                  alt="Photo to tattoo"
                  fill
                  className="object-cover object-center"
                  sizes="(max-width:639px) 100vw, 340px"
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
                  <span className="text-xs text-ink-100/45">Photo to Tattoo</span>
                </div>
                <Link href="/flow/photo_convert" className="text-xs text-accent font-medium hover:underline flex items-center gap-1">
                  Try it <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
            <SplitCard before="/showcase/ab2.png" after="/showcase/ali-blur-after-copy.png" bodyPart="Male Forearm" style="Blackwork" />
            <SplitCard before="/showcase/before-arm.jpeg" after="/showcase/arm-after2.png" bodyPart="Male Forearm" style="Japanese Color" />
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

      <div className="w-full max-w-5xl mx-auto px-4 sm:px-5">
        <HealingJourney />
      </div>

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

      <section className="w-full px-4 sm:px-5 py-12 border-t border-ink-800/60">
        <div className="w-full max-w-2xl mx-auto text-center">
          <span className="inline-block font-display text-xl text-accent mb-3 tracking-tight">TattooVisionAI</span>
          <h2 className="font-display text-2xl md:text-3xl text-ink-100 mb-3 leading-snug">
            Ink is permanent. Your decision shouldn&apos;t be a guess.
          </h2>
          <p className="text-sm text-ink-100/55 leading-relaxed mb-2">
            We built TattooVisionAI for everyone who&apos;s ever wanted a tattoo but feared the &ldquo;what if it looks wrong&rdquo;.
            Try designs on your real skin, transform a scar into art, or see how today&apos;s ink ages in 15 years — risk-free.
          </p>
          <p className="text-xs text-ink-100/35">
            Made by people who get inked. Share your preview and tag <span className="text-accent/70 font-medium">#TattooVisionAI</span>.
          </p>
        </div>
      </section>

      <section className="w-full px-4 sm:px-5 py-12">
        <div className="w-full max-w-3xl mx-auto">
          <p className="text-accent text-xs font-medium tracking-wider uppercase mb-2 text-center">Simple pricing</p>
          <h2 className="font-display text-2xl md:text-3xl text-ink-100 text-center mb-2">Start free. Pay only if you love it.</h2>
          <p className="text-sm text-ink-100/55 text-center mb-8 max-w-lg mx-auto">
            No subscription. No account. Just previews when you want them.
          </p>

          <div className="grid sm:grid-cols-2 gap-4">
            <div className="rounded-2xl border border-border bg-ink-900/60 p-6 flex flex-col">
              <span className="text-xs font-bold uppercase tracking-widest text-ink-100/45 mb-3">Free start</span>
              <div className="text-3xl font-bold text-ink-100 mb-1">$0</div>
              <p className="text-sm text-ink-100/50 mb-5">2 AI previews on the house</p>
              <ul className="space-y-2.5 mb-6 flex-1">
                {['2 free AI tattoo previews', 'Every flow unlocked', 'No card, no sign-up'].map((t) => (
                  <li key={t} className="flex items-start gap-2.5 text-sm text-ink-100/70">
                    <CheckCircle2 className="w-4 h-4 text-accent/60 shrink-0 mt-0.5" /> {t}
                  </li>
                ))}
              </ul>
              <Link
                href="/design"
                className="w-full text-center rounded-xl border border-border bg-ink-800 py-3 text-sm font-semibold text-ink-100 hover:border-ink-100/20 transition"
              >
                Start free
              </Link>
            </div>

            <div className="relative rounded-2xl border border-accent/40 bg-ink-900 p-6 flex flex-col shadow-lg shadow-accent/10">
              <span className="absolute -top-2.5 right-5 text-[10px] font-bold uppercase tracking-widest bg-accent text-ink-950 px-2.5 py-1 rounded-full">
                Best value
              </span>
              <span className="text-xs font-bold uppercase tracking-widest text-accent mb-3">5-pack</span>
              <div className="text-3xl font-bold text-ink-100 mb-1">
                $1 <span className="text-base font-medium text-ink-100/45">one-time</span>
              </div>
              <p className="text-sm text-ink-100/50 mb-5">5 more concepts — about 20¢ each</p>
              <ul className="space-y-2.5 mb-6 flex-1">
                {['5 AI-generated concepts', 'Cover-up, fade, couple & more', 'Pay securely — Visa / Mastercard'].map((t) => (
                  <li key={t} className="flex items-start gap-2.5 text-sm text-ink-100/80">
                    <CheckCircle2 className="w-4 h-4 text-accent shrink-0 mt-0.5" /> {t}
                  </li>
                ))}
              </ul>
              <Link
                href="/design"
                className="w-full text-center rounded-xl bg-accent py-3 text-sm font-bold text-ink-950 hover:bg-accent/90 active:scale-[0.98] transition"
              >
                Get 5 concepts — $1
              </Link>
            </div>
          </div>

          <p className="flex items-center justify-center gap-1.5 text-center text-xs text-ink-100/45 mt-5">
            <Clock className="w-3.5 h-3.5 text-accent/60" />
            Launch pricing — locked in while we&apos;re new. Most people land their design in under 5 minutes.
          </p>
        </div>
      </section>

      <p className="w-full text-center text-[11px] text-ink-100/20 py-5 px-4 sm:px-5">
        Visual simulations only. Always consult a professional tattoo artist. Not medical advice.{' '}
        <Link href="/compare" className="text-accent/35 hover:underline">
          Compare tray →
        </Link>
      </p>
    </PageShell>
  )
}
