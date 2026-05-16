'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { Bookmark, ChevronLeft, Heart, LayoutGrid, Loader2, Plus, Share2 } from 'lucide-react'
import type { ConceptResult, FlowAnswers, FlowId, GenerateResponse } from '@/lib/types'
import { generateCoupleTattoos, generateTattoos, checkCredits } from '@/lib/api'
import { saveConcept } from '@/lib/storage'
import { BeforeAfterSlider } from './BeforeAfterSlider'
import { PaymentScreen } from './PaymentScreen'

export function ResultScreen({
  flowTitle,
  flowId,
  data,
  bodyPhoto,
  answers,
  referenceImage,
  couplePhotos,
  onBack,
  onAppendConcepts,
}: {
  flowTitle: string
  flowId: FlowId
  data: GenerateResponse
  bodyPhoto: File | null
  answers: FlowAnswers
  /** Photo-convert flow: same reference as first run */
  referenceImage?: File | null
  couplePhotos?: { a: File; b: File }
  onBack: () => void
  onAppendConcepts: (more: GenerateResponse) => void
}) {
  const [selected, setSelected] = useState(0)
  const concept = data.concepts[selected]
  const [savedToast, setSavedToast] = useState(false)
  const [shareToast, setShareToast] = useState<string | null>(null)
  const [moreLoading, setMoreLoading] = useState(false)
  const [moreError, setMoreError] = useState<string | null>(null)
  const [showPaywall, setShowPaywall] = useState(false)
  const isFade = flowId === 'tattoo_fade'
  const [showCompare, setShowCompare] = useState(flowId === 'scar_coverup' || isFade)
  const prevCount = useRef(data.concepts.length)

  const isScar = flowId === 'scar_coverup'
  const isCouple = flowId === 'couple_tattoo'
  const isSelfHarm = isScar && answers.scar_type === 'self_harm'

  const fadeYearsLabel = isFade
    ? answers.fade_strength === 'subtle'
      ? '~2-3 yrs'
      : answers.fade_strength === 'heavy'
      ? '~10-15 yrs'
      : '~5-7 yrs'
    : ''

  // Create + revoke the object URL inside the SAME effect — in React 18
  // Strict Mode the cleanup fires immediately after mount, and a useMemo
  // value isn't recomputed on remount, which would leave us pointing at a
  // revoked URL. Owning the lifetime in one effect avoids that.
  const [beforeUrl, setBeforeUrl] = useState<string>('')
  useEffect(() => {
    if (!bodyPhoto) return
    const url = URL.createObjectURL(bodyPhoto)
    setBeforeUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [bodyPhoto])

  useEffect(() => {
    if (data.concepts.length > prevCount.current) {
      setSelected(data.concepts.length - 1)
    }
    prevCount.current = data.concepts.length
  }, [data.concepts.length])

  function dataUrl(c: ConceptResult) {
    return `data:${c.media_type};base64,${c.image_base64}`
  }

  function handleSave(c: ConceptResult) {
    saveConcept({
      savedAt: new Date().toISOString(),
      flowId,
      flowTitle,
      concept: c,
      fitScore: c.advisory_score ?? data.fit.score,
      previewDataUrl: dataUrl(c),
    })
    setSavedToast(true)
    setTimeout(() => setSavedToast(false), 2000)
  }

  async function handleShare(c: ConceptResult) {
    try {
      const res = await fetch(dataUrl(c))
      const blob = await res.blob()
      const file = new File([blob], 'tattoo-coverup.jpg', { type: blob.type })
      const shareData: ShareData = {
        title: isCouple ? 'Our couple tattoo preview' : 'My tattoo design',
        text:
          isCouple
            ? 'Couple tattoo preview made with Tattoo Advisor.'
            : 'Tattoo preview made with Tattoo Advisor.',
        files: [file],
      }
      if (
        typeof navigator !== 'undefined' &&
        'canShare' in navigator &&
        navigator.canShare?.(shareData) &&
        'share' in navigator
      ) {
        await navigator.share(shareData)
        setShareToast('Shared')
      } else {
        const link = document.createElement('a')
        link.href = dataUrl(c)
        link.download = isCouple ? 'couple-tattoo.jpg' : 'tattoo-preview.jpg'
        link.click()
        setShareToast('Downloaded — share it anywhere')
      }
    } catch {
      setShareToast('Could not share — try saving instead')
    } finally {
      setTimeout(() => setShareToast(null), 2500)
    }
  }

  async function addOneVariation() {
    // Check credits before making the call
    const currentCredits = await checkCredits()
    if (currentCredits <= 0) {
      setShowPaywall(true)
      return
    }

    setMoreLoading(true)
    setMoreError(null)
    try {
      const coupleAnswers: FlowAnswers =
        isCouple && data.couple?.pair_id
          ? { ...answers, couple_pair_id: data.couple.pair_id }
          : answers
      const isSplit = isCouple && String(answers.couple_mode || '') === 'complementary_split'
      const more =
        isSplit
          ? await generateCoupleTattoos(null, null, coupleAnswers)
          : isCouple && couplePhotos
          ? await generateCoupleTattoos(couplePhotos.a, couplePhotos.b, coupleAnswers)
          : await generateTattoos(bodyPhoto as File, flowId, coupleAnswers, 1, referenceImage ?? null)
      onAppendConcepts(more)
    } catch (e) {
      if ((e as any)?.status === 402) {
        setShowPaywall(true)
        return
      }
      setMoreError(e instanceof Error ? e.message : 'Could not add variation')
    } finally {
      setMoreLoading(false)
    }
  }

  const lastScore = data.concepts[data.concepts.length - 1]?.advisory_score
  const hintA = lastScore != null ? Math.max(72, lastScore - 3) : 88
  const hintB = lastScore != null ? Math.min(98, lastScore + 4) : 96

  const cols = data.concepts.length === 1 ? 'grid-cols-1' : 'md:grid-cols-2 lg:grid-cols-3'

  if (showPaywall) {
    return <PaymentScreen onBack={() => setShowPaywall(false)} />
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      <button
        type="button"
        onClick={onBack}
        className="text-sm text-ink-100/50 hover:text-ink-100 mb-4 inline-flex items-center gap-1"
      >
        <ChevronLeft className="w-4 h-4" /> New run
      </button>

      {isScar && (
        <div
          className={
            isSelfHarm
              ? 'mb-6 rounded-2xl border border-accent/40 bg-gradient-to-br from-accent/10 to-ink-900/60 p-5'
              : 'mb-6 rounded-2xl border border-border bg-ink-900/50 p-5'
          }
        >
          <div className="flex items-start gap-3">
            <Heart
              className={
                isSelfHarm
                  ? 'w-5 h-5 text-accent shrink-0 mt-0.5'
                  : 'w-5 h-5 text-accent/70 shrink-0 mt-0.5'
              }
            />
            <div>
              <p className="text-sm font-medium text-ink-100">
                {isSelfHarm
                  ? 'You took a brave step.'
                  : 'A cover-up is a transformation.'}
              </p>
              <p className="text-sm text-ink-100/70 mt-1">
                {isSelfHarm
                  ? 'These previews are a planning tool — not a finished journey. Take your time, talk to a licensed artist, and reach out to support if you need it.'
                  : 'Slide the line below to compare your photo with the proposed cover-up. Share it, save it, or refine it.'}
              </p>
              {isSelfHarm && (
                <div className="mt-3 flex flex-wrap gap-2">
                  <a
                    href="https://findahelpline.com"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs rounded-full border border-accent/40 px-3 py-1 text-accent/90 hover:bg-accent/10"
                  >
                    Find a helpline →
                  </a>
                  <a
                    href="https://www.crisistextline.org/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs rounded-full border border-accent/40 px-3 py-1 text-accent/90 hover:bg-accent/10"
                  >
                    Crisis text line →
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="flex flex-col lg:flex-row gap-6 mb-8">
        <div className="flex-1 min-w-0">
          {concept && showCompare && !isCouple ? (
            <BeforeAfterSlider
              beforeSrc={beforeUrl}
              afterSrc={dataUrl(concept)}
              beforeLabel={isScar ? 'Scar' : isFade ? 'Today' : 'Before'}
              afterLabel={isScar ? 'Cover-up' : isFade ? `Faded ${fadeYearsLabel}` : 'After'}
            />
          ) : (
            <div className="rounded-2xl border border-border bg-ink-900/50 overflow-hidden">
              {concept && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={dataUrl(concept)}
                  alt="Tattoo preview"
                  className="w-full h-auto max-h-[65vh] object-contain bg-black/40"
                />
              )}
            </div>
          )}

          {concept && !isCouple && (
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setShowCompare((v) => !v)}
                className="text-xs rounded-full border border-border px-3 py-1.5 text-ink-100/80 hover:bg-ink-800/60"
              >
                {showCompare ? 'View design only' : 'Compare before / after'}
              </button>
              <button
                type="button"
                onClick={() => handleShare(concept)}
                className="inline-flex items-center gap-1.5 text-xs rounded-full border border-accent/40 px-3 py-1.5 text-accent hover:bg-accent/10"
              >
                <Share2 className="w-3.5 h-3.5" /> Share
              </button>
            </div>
          )}
        </div>

        {concept && (
          <div className="lg:w-72 shrink-0 rounded-2xl border border-border bg-ink-900/60 p-5 flex flex-col gap-3">
            <p className="text-2xl font-semibold text-accent">
              {isFade
                ? fadeYearsLabel
                : concept.advisory_score != null
                ? `${concept.advisory_score}%`
                : '—'}
              <span className="text-sm font-normal text-ink-100/50 ml-2">
                {isFade ? 'simulated wear' : 'advisory fit'}
              </span>
            </p>
            <div>
              <p className="text-sm text-ink-100/70">{concept.style_label}</p>
              <p className="text-sm text-ink-100/55">{concept.coverage_label}</p>
            </div>
            <p className="text-sm text-ink-100/80 leading-relaxed">{concept.explanation}</p>
            <div className="mt-auto pt-3 flex flex-col gap-2">
              <button
                type="button"
                onClick={() => handleSave(concept)}
                className="inline-flex items-center justify-center gap-2 rounded-full border border-border px-4 py-2 text-sm text-ink-100 hover:bg-ink-800/80 w-full"
              >
                <Bookmark className="w-4 h-4" /> Save concept
              </button>
              <Link
                href="/compare"
                className="inline-flex items-center justify-center gap-2 rounded-full bg-accent px-4 py-2 text-sm font-medium text-ink-950 w-full"
              >
                <LayoutGrid className="w-4 h-4" /> Compare saved
              </Link>
            </div>
          </div>
        )}
      </div>

      {data.concepts.length > 1 && (
        <div className={`grid gap-4 mb-6 grid-cols-2 md:grid-cols-3 lg:grid-cols-4`}>
          {data.concepts.map((c, i) => (
            <button
              key={`${c.id}-${i}`}
              type="button"
              onClick={() => setSelected(i)}
              className={`rounded-xl border text-left overflow-hidden transition ${
                selected === i ? 'border-accent ring-1 ring-accent/30' : 'border-border hover:border-ink-100/20'
              }`}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={dataUrl(c)} alt="" className="w-full h-24 object-cover" />
              <div className="p-2">
                <p className="text-sm font-semibold text-accent">
                  {c.advisory_score != null ? `${c.advisory_score}%` : '—'}
                </p>
                <p className="text-xs text-ink-100/55 mt-0.5">{c.style_label}</p>
              </div>
            </button>
          ))}
        </div>
      )}

      <div className="mb-8">
        <button
          type="button"
          disabled={moreLoading || data.concepts.length >= 6 || (isCouple && !couplePhotos)}
          onClick={addOneVariation}
          className="inline-flex items-center gap-2 rounded-full border border-accent/40 px-4 py-2 text-sm text-accent hover:bg-accent/10 disabled:opacity-40"
        >
          {moreLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          {moreLoading ? 'Working…' : 'Add one more variation'}
        </button>
        <p className="text-xs text-ink-100/45 mt-2 max-w-md">
          {isFade
            ? `Extra runs explore nearby fade textures at the same ${fadeYearsLabel} mark — useful if a particular result feels too aggressive or too soft.`
            : `Extra runs explore nearby fits — you might see something closer to a ${hintA}% or ${hintB}% advisory readout than your current pick (not guaranteed; each run is fresh).`}
        </p>
      </div>
      {moreError && <p className="text-sm text-red-400/90 mb-6">{moreError}</p>}

      <p className="text-sm text-ink-100/50 mb-8">
        {isFade
          ? 'Aging simulation only — actual fade depends on placement, sun exposure, skin type and aftercare. Use this as a long-term planning aid, not a guarantee.'
          : 'Preview uses your photo\u2019s skin tone and lighting \u2014 not a prediction of healed ink. Discuss details with a licensed artist.'}
      </p>

      {concept && !isFade && (
        <div className="rounded-2xl border border-border bg-ink-900/60 p-6 mb-8">
          <h3 className="font-display text-xl text-ink-100 mb-2">
            Overall advisory fit: {data.fit.score}
          </h3>
          <p className="text-sm text-ink-100/65 mb-4">{data.fit.summary}</p>
          <ul className="grid sm:grid-cols-2 gap-2 text-xs text-ink-100/55">
            {data.fit.factors.map((f) => (
              <li key={f.key} className="flex justify-between gap-2 border border-border/60 rounded-lg px-2 py-1.5">
                <span>{f.label}</span>
                <span className="text-ink-100/80">{f.value}</span>
              </li>
            ))}
          </ul>
          <p className="text-xs text-ink-100/35 mt-4">{data.disclaimer}</p>
        </div>
      )}

      {concept && isFade && (
        <div className="rounded-2xl border border-border bg-ink-900/60 p-6 mb-8">
          <h3 className="font-display text-xl text-ink-100 mb-2">
            Aging simulation · {fadeYearsLabel}
          </h3>
          <p className="text-sm text-ink-100/65">
            Drag the slider above to compare today vs. simulated wear. Real-world
            fading depends on placement, sun exposure, skin type and aftercare —
            this is a planning aid, not a medical or dermatological prediction.
          </p>
          <p className="text-xs text-ink-100/35 mt-4">{data.disclaimer}</p>
        </div>
      )}

      {savedToast && (
        <p className="text-sm text-accent mt-3">Saved — open Compare to see side by side.</p>
      )}
      {shareToast && <p className="text-sm text-accent mt-3">{shareToast}</p>}
    </div>
  )
}
