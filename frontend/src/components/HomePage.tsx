'use client'

import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  Eye,
  Loader2,
  Shield,
  Sparkles,
} from 'lucide-react'
import { PhotoUploader } from './PhotoUploader'
import { PageShell } from './PageShell'
import {
  clearPendingBodyPhoto,
  storePendingBodyPhoto,
  FLOW_RESULT_KEY,
  hasPendingBodyPhoto,
} from '@/lib/pendingPhoto'

const LOG = process.env.NODE_ENV === 'development'
function log(...args: unknown[]) {
  if (LOG) console.log('[HomePage]', ...args)
}

const TRUST = [
  { icon: Shield, t: 'Private & secure', d: 'Photos used only for your preview' },
  { icon: Sparkles, t: 'No sign-up', d: 'Start instantly — no account' },
  { icon: Eye, t: 'Real previews', d: 'See ink on your own skin' },
  { icon: Clock, t: 'Under 5 minutes', d: 'From upload to design' },
]

const FLOW_PATH = '/flow/new_to_tattoos'

export function HomePage() {
  const router = useRouter()
  const [bodyPhoto, setBodyPhoto] = useState<File | null>(null)
  const [photoPreparing, setPhotoPreparing] = useState(false)
  const [photoReady, setPhotoReady] = useState(false)
  const [navigating, setNavigating] = useState(false)
  const [navError, setNavError] = useState<string | null>(null)
  const [highlightUpload, setHighlightUpload] = useState(false)
  const [paymentBanner, setPaymentBanner] = useState<{ credits: number } | null>(null)
  const navLock = useRef(false)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const p = new URLSearchParams(window.location.search)
    if (p.get('payment') === 'success') {
      setPaymentBanner({ credits: parseInt(p.get('credits') || '5', 10) })
      window.history.replaceState({}, '', window.location.pathname)
      setTimeout(() => setPaymentBanner(null), 6000)
    }
  }, [])

  function scrollToUpload() {
    document.getElementById('upload')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    setHighlightUpload(true)
    setTimeout(() => setHighlightUpload(false), 2000)
  }

  async function preparePhoto(file: File) {
    setPhotoPreparing(true)
    setNavError(null)
    log('preparePhoto start', file.name)
    // storePendingBodyPhoto sets in-memory handoff synchronously before compress
    const storePromise = storePendingBodyPhoto(file)
    setPhotoReady(true)
    try {
      await storePromise
      log('preparePhoto backup done')
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Could not prepare photo'
      console.error('[HomePage] preparePhoto failed:', err)
      setNavError(msg)
      setPhotoReady(false)
    } finally {
      setPhotoPreparing(false)
    }
  }

  function handlePhotoChange(file: File | null) {
    setBodyPhoto(file)
    setNavError(null)
    if (!file) {
      clearPendingBodyPhoto()
      setPhotoReady(false)
      setPhotoPreparing(false)
      return
    }
    void preparePhoto(file)
  }

  async function continueToQuestions() {
    if (navLock.current || navigating) {
      log('continue blocked — already navigating')
      return
    }
    if (!bodyPhoto) {
      scrollToUpload()
      return
    }

    navLock.current = true
    setNavigating(true)
    setNavError(null)
    log('continueToQuestions click')

    try {
      if (!photoReady || !hasPendingBodyPhoto()) {
        log('photo not ready yet, preparing…')
        await storePendingBodyPhoto(bodyPhoto)
        setPhotoReady(true)
      }

      try {
        sessionStorage.removeItem(FLOW_RESULT_KEY('new_to_tattoos'))
      } catch {}

      log('router.push →', FLOW_PATH)
      await router.push(FLOW_PATH)

      // Last resort only — full reload clears in-memory handoff (sessionStorage backup must exist)
      window.setTimeout(() => {
        if (window.location.pathname === '/' || window.location.pathname === '') {
          log('router.push stalled — hard redirect (requires sessionStorage backup)')
          window.location.assign(FLOW_PATH)
        }
      }, 2500)
    } catch (err) {
      navLock.current = false
      setNavigating(false)
      const msg = err instanceof Error ? err.message : 'Navigation failed'
      console.error('[HomePage] continueToQuestions failed:', err)
      setNavError(msg)
    }
    // Do NOT setNavigating(false) on success — stay in loading state until page unmounts
  }

  const canContinue = Boolean(bodyPhoto) && photoReady && !photoPreparing && !navigating
  const continueLabel = photoPreparing
    ? 'Preparing photo…'
    : navigating
    ? 'Opening questions…'
    : 'Continue to questions'

  return (
    <PageShell className="min-h-screen bg-ink-950 text-ink-100">
      {paymentBanner && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 rounded-2xl border border-accent/30 bg-ink-900 px-5 py-3 shadow-2xl pointer-events-auto">
          <CheckCircle2 className="w-5 h-5 text-accent shrink-0" />
          <span className="text-sm font-medium">
            Payment successful — {paymentBanner.credits} credits added!
          </span>
        </div>
      )}

      <div className="w-full max-w-2xl mx-auto px-4 sm:px-5">
        <section className="pt-7 sm:pt-10 pb-4 text-center">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-accent/40 bg-accent/10 px-3 py-1 text-[11px] sm:text-xs font-bold tracking-wide text-accent">
            <Sparkles className="w-3.5 h-3.5" /> 1 FREE PREVIEW · NO CARD NEEDED
          </span>
          <h1 className="font-display text-3xl sm:text-4xl font-semibold leading-tight mt-3 mb-2">
            See your tattoo on your body
            <span className="text-accent"> before you commit.</span>
          </h1>

          <div className="flex flex-col items-center gap-3 w-full max-w-md mx-auto">
            <p className="text-ink-100/55 text-sm text-center leading-relaxed">
              Upload a photo, answer 2 questions, preview on your real skin.
            </p>
            <p className="flex items-start sm:items-center justify-center gap-1.5 text-xs text-accent/90 font-medium text-center leading-snug px-1">
              <Shield className="w-3.5 h-3.5 shrink-0 mt-0.5 sm:mt-0" />
              <span>We don&apos;t save your photos — deleted after your preview</span>
            </p>

            <div className="w-full flex justify-center pt-1">
              {!bodyPhoto ? (
                <a
                  href="#upload"
                  onClick={(e) => {
                    e.preventDefault()
                    scrollToUpload()
                  }}
                  className="inline-flex items-center justify-center gap-2.5 rounded-full bg-accent px-8 py-4 text-ink-950 font-bold text-base hover:bg-accent/90 active:scale-[0.97] transition shadow-lg shadow-accent/30 animate-cta-pulse cursor-pointer touch-manipulation whitespace-nowrap"
                >
                  Start my tattoo preview
                  <ArrowRight className="w-5 h-5" />
                </a>
              ) : (
                <button
                  type="button"
                  onClick={continueToQuestions}
                  disabled={!canContinue}
                  className="inline-flex items-center justify-center gap-2.5 rounded-full bg-accent px-8 py-4 text-ink-950 font-bold text-base hover:bg-accent/90 active:scale-[0.97] transition shadow-lg shadow-accent/30 animate-cta-pulse touch-manipulation disabled:opacity-60 disabled:animate-none whitespace-nowrap"
                >
                  {(photoPreparing || navigating) && <Loader2 className="w-5 h-5 animate-spin" />}
                  {continueLabel}
                  {!photoPreparing && !navigating && <ArrowRight className="w-5 h-5" />}
                </button>
              )}
            </div>

            <p className="text-xs text-ink-100/50 text-center">
              <span className="text-accent font-semibold">1 preview free</span> — no sign-up, no card. Then 5 more for{' '}
              <span className="text-ink-100/75 font-semibold">$5</span>.
            </p>
          </div>
        </section>

        <section className="pb-5">
          <p className="text-accent text-[10px] font-bold tracking-wider uppercase mb-2 text-center">
            Real before &amp; after
          </p>
          <div className="rounded-xl overflow-hidden border border-border bg-ink-900">
            <div className="flex h-36 sm:h-44">
              <div className="relative w-1/2 bg-ink-950">
                <Image src="/showcase/before-arm.jpeg" alt="Before" fill className="object-cover" sizes="50vw" priority />
                <span className="absolute bottom-1.5 left-1.5 text-[9px] font-bold bg-ink-950/85 text-ink-100/70 px-1.5 py-0.5 rounded">BEFORE</span>
              </div>
              <div className="relative w-1/2 bg-ink-950">
                <Image src="/showcase/arm-after2.png" alt="AI Preview" fill className="object-cover" sizes="50vw" priority />
                <span className="absolute bottom-1.5 right-1.5 text-[9px] font-bold bg-accent text-ink-950 px-1.5 py-0.5 rounded">AI PREVIEW</span>
              </div>
            </div>
          </div>
        </section>

        <section className="pb-6">
          <div
            id="upload"
            className={`scroll-mt-4 rounded-2xl transition-shadow duration-300 ${
              highlightUpload ? 'ring-2 ring-accent/60 shadow-lg shadow-accent/10' : ''
            }`}
          >
            <p className="text-sm font-semibold text-ink-100 mb-2">Step 1 — Upload your body photo</p>
            <PhotoUploader
              value={bodyPhoto}
              onChange={handlePhotoChange}
              compact
              hint="Pick a photo — wait for ✓ Ready, then tap Continue."
            />

            {photoPreparing && (
              <p className="text-xs text-ink-100/50 mt-2 flex items-center gap-1.5">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-accent" /> Compressing photo…
              </p>
            )}
            {photoReady && !photoPreparing && bodyPhoto && (
              <p className="text-xs text-accent mt-2 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" /> Photo ready — tap Continue when you&apos;re set.
              </p>
            )}

            {bodyPhoto && (
              <button
                type="button"
                onClick={continueToQuestions}
                disabled={!canContinue}
                className="mt-3 w-full inline-flex items-center justify-center gap-2 rounded-full bg-accent px-5 py-3.5 text-ink-950 font-bold text-sm shadow-lg shadow-accent/25 touch-manipulation disabled:opacity-60 disabled:shadow-none"
              >
                {(photoPreparing || navigating) && <Loader2 className="w-4 h-4 animate-spin" />}
                {continueLabel}
                {!photoPreparing && !navigating && <ArrowRight className="w-4 h-4" />}
              </button>
            )}

            {navError && (
              <p className="text-xs text-red-400/90 mt-2">{navError}</p>
            )}
          </div>

          <div className="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-2">
            {TRUST.map((b) => (
              <div
                key={b.t}
                className="rounded-xl border border-border/70 bg-ink-900/50 px-3 py-3 text-left"
              >
                <div className="flex items-center gap-1.5 mb-1">
                  <b.icon className="w-3.5 h-3.5 text-accent shrink-0" />
                  <p className="text-[11px] sm:text-xs font-semibold text-ink-100 leading-tight">{b.t}</p>
                </div>
                <p className="text-[10px] text-ink-100/45 leading-snug pl-5">{b.d}</p>
              </div>
            ))}
          </div>
        </section>

        <p className="text-center text-[10px] text-ink-100/30 pb-6">
          Visual simulations only · Consult a professional artist
        </p>
      </div>
    </PageShell>
  )
}
