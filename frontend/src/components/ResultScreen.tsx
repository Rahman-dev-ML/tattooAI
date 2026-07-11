'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { Bookmark, ChevronLeft, Download, LayoutGrid, Loader2, Share2, Sparkles, Zap } from 'lucide-react'
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
  onCreditsChange,
}: {
  flowTitle: string
  flowId: FlowId
  data: GenerateResponse
  bodyPhoto: File | null
  answers: FlowAnswers
  referenceImage?: File | null
  couplePhotos?: { a: File; b: File }
  onBack: () => void
  onAppendConcepts: (more: GenerateResponse) => void
  onCreditsChange?: (credits: number) => void
}) {
  const [selected, setSelected] = useState(0)
  const concept = data.concepts[selected]
  const [savedToast, setSavedToast] = useState(false)
  const [shareToast, setShareToast] = useState<string | null>(null)
  const [moreLoading, setMoreLoading] = useState(false)
  const [moreError, setMoreError] = useState<string | null>(null)
  const [showPaywall, setShowPaywall] = useState(false)
  const [credits, setCredits] = useState<number | null>(null)
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

  const [beforeUrl, setBeforeUrl] = useState<string>('')
  useEffect(() => {
    if (!bodyPhoto) return
    const url = URL.createObjectURL(bodyPhoto)
    setBeforeUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [bodyPhoto])

  useEffect(() => {
    checkCredits().then(setCredits)
  }, [])

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

  function handleDownload(c: ConceptResult) {
    const link = document.createElement('a')
    link.href = dataUrl(c)
    link.download = isCouple ? 'couple-tattoo-preview.jpg' : `tattoo-preview-${flowId}.jpg`
    link.click()
  }

  async function handleShare(c: ConceptResult) {
    const siteUrl = 'https://tattoovisionai.com'
    const shareText = isCouple
      ? `Our couple tattoo preview — designed with AI ✨ ${siteUrl}`
      : `My tattoo design — visualised with AI before committing ✨ ${siteUrl}`
    try {
      const res = await fetch(dataUrl(c))
      const blob = await res.blob()
      const file = new File([blob], 'tattoo-preview.jpg', { type: blob.type })
      const shareData: ShareData = {
        title: isCouple ? 'Our couple tattoo preview' : 'My tattoo design',
        text: shareText,
        files: [file],
      }
      if (
        typeof navigator !== 'undefined' &&
        'canShare' in navigator &&
        navigator.canShare?.(shareData) &&
        'share' in navigator
      ) {
        await navigator.share(shareData)
        setShareToast('Shared!')
      } else if (typeof navigator !== 'undefined' && 'share' in navigator) {
        await navigator.share({ title: 'TattooVisionAI', text: shareText, url: siteUrl })
        setShareToast('Shared!')
      } else {
        try {
          await window.navigator.clipboard.writeText(shareText)
          setShareToast('Link copied — paste to share!')
        } catch {
          setShareToast('Could not share — try downloading instead')
        }
        return
      }
    } catch {
      setShareToast('Could not share — try downloading instead')
    } finally {
      setTimeout(() => setShareToast(null), 2500)
    }
  }

  async function addOneVariation() {
    const currentCredits = await checkCredits()
    setCredits(currentCredits)
    if (currentCredits <= 0) {
      onCreditsChange?.(0)
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

      const answersWithOffset: FlowAnswers = {
        ...coupleAnswers,
        run_offset: String(data.concepts.length),
      }

      const isSplit = isCouple && String(answers.couple_mode || '') === 'complementary_split'
      const more =
        isSplit
          ? await generateCoupleTattoos(null, null, answersWithOffset)
          : isCouple && couplePhotos
          ? await generateCoupleTattoos(couplePhotos.a, couplePhotos.b, answersWithOffset)
          : await generateTattoos(bodyPhoto, flowId, answersWithOffset, 1, referenceImage ?? null)

      if ((more as { creditsRemaining?: number }).creditsRemaining !== undefined) {
        const remaining = (more as { creditsRemaining?: number }).creditsRemaining!
        setCredits(remaining)
        onCreditsChange?.(remaining)
      } else {
        setCredits((c) => (c != null ? Math.max(0, c - 1) : c))
      }

      onAppendConcepts(more)
    } catch (e) {
      if ((e as { status?: number }).status === 402) {
        onCreditsChange?.(0)
        setCredits(0)
        setShowPaywall(true)
        return
      }
      setMoreError(e instanceof Error ? e.message : 'Could not generate another design')
    } finally {
      setMoreLoading(false)
    }
  }

  const outOfCredits = credits !== null && credits <= 0
  const generateLabel = moreLoading
    ? 'Generating…'
    : outOfCredits
    ? 'Get 5 more previews — $5'
    : 'Generate another design'
  const generateSubtext = outOfCredits
    ? 'You used your free preview. Unlock 5 more styles.'
    : credits === 1
    ? '1 free preview left — try a different style'
    : credits != null && credits > 1
    ? `${credits} previews left — explore more styles`
    : 'Try a different style on your photo'

  const canGenerateMore = !moreLoading && data.concepts.length < 6 && !(isCouple && !couplePhotos)

  if (showPaywall) {
    return <PaymentScreen onBack={() => setShowPaywall(false)} />
  }

  function GenerateMoreButton({
    className = '',
    size = 'large',
  }: {
    className?: string
    size?: 'large' | 'compact'
  }) {
    const compact = size === 'compact'
    const label = moreLoading
      ? 'Generating…'
      : outOfCredits
      ? 'Get 5 more previews — $5'
      : compact
      ? 'Generate another design'
      : generateLabel

    return (
      <div className={className}>
        <button
          type="button"
          disabled={!canGenerateMore}
          onClick={addOneVariation}
          className={`w-full inline-flex items-center justify-center gap-2 rounded-full font-bold transition active:scale-[0.98] disabled:opacity-50 bg-accent text-ink-950 shadow-lg shadow-accent/30 animate-cta-pulse touch-manipulation ${
            compact ? 'px-4 py-2.5 text-sm' : 'px-5 py-3.5 text-base'
          }`}
        >
          {moreLoading ? (
            <Loader2 className={compact ? 'w-4 h-4 animate-spin' : 'w-5 h-5 animate-spin'} />
          ) : outOfCredits ? (
            <Zap className={compact ? 'w-4 h-4' : 'w-5 h-5'} />
          ) : (
            <Sparkles className={compact ? 'w-4 h-4' : 'w-5 h-5'} />
          )}
          {label}
        </button>
        {!compact && (
          <>
            <p className="text-center text-[11px] text-ink-100/45 mt-1.5">{generateSubtext}</p>
            {moreError && <p className="text-xs text-red-400/90 mt-2 text-center">{moreError}</p>}
          </>
        )}
        {compact && moreError && (
          <p className="text-[10px] text-red-400/90 mt-1 text-center">{moreError}</p>
        )}
      </div>
    )
  }

  return (
    <>
    <div className="max-w-5xl mx-auto px-4 pt-4 pb-24 w-full">
        <button
          type="button"
          onClick={onBack}
          className="text-xs text-ink-100/50 hover:text-ink-100 mb-3 inline-flex items-center gap-1"
        >
          <ChevronLeft className="w-4 h-4" /> Start over
        </button>

        {isScar && isSelfHarm && (
          <div className="mb-4 rounded-xl border border-accent/40 bg-accent/5 p-3 text-xs text-ink-100/70">
            Take your time — these previews are for planning. Talk to a licensed artist when ready.
          </div>
        )}

        <div className="mb-3">
          <p className="text-xs font-medium text-accent mb-0.5">Your preview is ready</p>
          <h2 className="font-display text-lg text-ink-100">Like it? Try more styles on your skin.</h2>
        </div>

        <GenerateMoreButton className="mb-4" />

        <div className="rounded-2xl border border-border bg-ink-900/50 overflow-hidden mb-3">
          {concept && showCompare && !isCouple && beforeUrl ? (
            <BeforeAfterSlider
              beforeSrc={beforeUrl}
              afterSrc={dataUrl(concept)}
              beforeLabel={isScar ? 'Scar' : isFade ? 'Today' : 'Before'}
              afterLabel={isScar ? 'Cover-up' : isFade ? `Faded ${fadeYearsLabel}` : 'After'}
            />
          ) : (
            concept && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={dataUrl(concept)}
                alt="Tattoo preview"
                className="w-full h-auto max-h-[42dvh] sm:max-h-[55vh] object-contain bg-black/40"
              />
            )
          )}
        </div>

        {concept && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-4">
            {!isCouple && (
              <button
                type="button"
                onClick={() => setShowCompare((v) => !v)}
                className="group flex flex-col items-center gap-1.5 rounded-xl border border-border/70 bg-gradient-to-b from-ink-800/70 to-ink-900/50 px-3 py-3 text-xs font-semibold text-ink-100/90 hover:border-accent/45 hover:shadow-lg hover:shadow-accent/5 active:scale-[0.97] transition touch-manipulation"
              >
                <span className="rounded-full bg-accent/15 p-2 group-hover:bg-accent/25 transition">
                  <LayoutGrid className="w-4 h-4 text-accent" />
                </span>
                {showCompare ? 'Design only' : 'Compare'}
              </button>
            )}
            <button
              type="button"
              onClick={() => handleDownload(concept)}
              className="group flex flex-col items-center gap-1.5 rounded-xl border border-border/70 bg-gradient-to-b from-ink-800/70 to-ink-900/50 px-3 py-3 text-xs font-semibold text-ink-100/90 hover:border-accent/45 hover:shadow-lg hover:shadow-accent/5 active:scale-[0.97] transition touch-manipulation"
            >
              <span className="rounded-full bg-accent/15 p-2 group-hover:bg-accent/25 transition">
                <Download className="w-4 h-4 text-accent" />
              </span>
              Save
            </button>
            <button
              type="button"
              onClick={() => handleShare(concept)}
              className="group flex flex-col items-center gap-1.5 rounded-xl border border-accent/60 bg-gradient-to-b from-accent/20 to-accent/5 px-3 py-3 text-xs font-bold text-accent hover:from-accent/30 hover:to-accent/10 hover:shadow-lg hover:shadow-accent/15 active:scale-[0.97] transition touch-manipulation"
            >
              <span className="rounded-full bg-accent/25 p-2 group-hover:bg-accent/35 transition">
                <Share2 className="w-4 h-4" />
              </span>
              Share
            </button>
            <button
              type="button"
              onClick={() => handleSave(concept)}
              className="group flex flex-col items-center gap-1.5 rounded-xl border border-border/70 bg-gradient-to-b from-ink-800/70 to-ink-900/50 px-3 py-3 text-xs font-semibold text-ink-100/90 hover:border-accent/45 hover:shadow-lg hover:shadow-accent/5 active:scale-[0.97] transition touch-manipulation"
            >
              <span className="rounded-full bg-accent/15 p-2 group-hover:bg-accent/25 transition">
                <Bookmark className="w-4 h-4 text-accent" />
              </span>
              Bookmark
            </button>
          </div>
        )}

        {data.concepts.length > 1 && (
          <div className="grid gap-2 grid-cols-3 sm:grid-cols-4 mb-4">
            {data.concepts.map((c, i) => (
              <button
                key={`${c.id}-${i}`}
                type="button"
                onClick={() => setSelected(i)}
                className={`rounded-lg border text-left overflow-hidden transition ${
                  selected === i ? 'border-accent ring-1 ring-accent/30' : 'border-border'
                }`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={dataUrl(c)} alt="" className="w-full h-16 object-cover" />
                <div className="p-1.5">
                  <p className="text-[10px] font-semibold text-accent">
                    {c.advisory_score != null ? `${c.advisory_score}%` : `#${i + 1}`}
                  </p>
                </div>
              </button>
            ))}
          </div>
        )}

        {concept && (
          <div className="rounded-xl border border-border bg-ink-900/60 p-4 mb-4">
            <p className="text-lg font-semibold text-accent">
              {isFade ? fadeYearsLabel : concept.advisory_score != null ? `${concept.advisory_score}%` : '—'}
              <span className="text-xs font-normal text-ink-100/50 ml-2">
                {isFade ? 'simulated wear' : 'advisory fit'}
              </span>
            </p>
            <p className="text-xs text-ink-100/70 mt-1">{concept.style_label} · {concept.coverage_label}</p>
            <p className="text-xs text-ink-100/60 mt-2 leading-relaxed">{concept.explanation}</p>
          </div>
        )}

        {concept && !isFade && (
          <details className="rounded-xl border border-border bg-ink-900/40 mb-4">
            <summary className="px-4 py-3 text-xs font-medium text-ink-100/60 cursor-pointer">
              Fit breakdown · {data.fit.score}
            </summary>
            <div className="px-4 pb-4">
              <p className="text-xs text-ink-100/55 mb-2">{data.fit.summary}</p>
              <ul className="grid grid-cols-2 gap-1.5 text-[10px] text-ink-100/50">
                {data.fit.factors.map((f) => (
                  <li key={f.key} className="flex justify-between gap-1 border border-border/60 rounded px-2 py-1">
                    <span>{f.label}</span>
                    <span>{f.value}</span>
                  </li>
                ))}
              </ul>
              <p className="text-[10px] text-ink-100/35 mt-2">{data.disclaimer}</p>
            </div>
          </details>
        )}

        <Link
          href="/compare"
          className="inline-flex items-center gap-1.5 text-xs text-ink-100/40 hover:text-accent mb-4"
        >
          <LayoutGrid className="w-3.5 h-3.5" /> Compare saved designs
        </Link>

        {savedToast && <p className="text-xs text-accent mb-2">Saved — open Compare to see side by side.</p>}
        {shareToast && <p className="text-xs text-accent mb-2">{shareToast}</p>}
    </div>

    <div className="fixed bottom-0 inset-x-0 z-40 border-t border-accent/20 bg-ink-950/95 backdrop-blur-md px-4 py-2.5 pb-[max(0.625rem,env(safe-area-inset-bottom))] shadow-[0_-6px_24px_rgba(0,0,0,0.35)]">
      <div className="max-w-lg mx-auto">
        <GenerateMoreButton size="compact" />
        <p className="text-center text-[10px] text-ink-100/40 mt-1">
          {outOfCredits ? 'Unlock 5 more styles on your photo' : generateSubtext}
        </p>
      </div>
    </div>
    </>
  )
}
