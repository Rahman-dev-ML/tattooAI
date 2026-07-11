'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { ChevronLeft, ChevronRight, Loader2 } from 'lucide-react'
import type { FlowAnswers, FlowId, GenerateResponse } from '@/lib/types'
import { FLOW_CONFIGS, getActiveSteps, type StepDef } from '@/lib/flowConfigs'
import { generateCoupleTattoos, generateTattoos, checkCredits, getDeviceId, initDeviceId } from '@/lib/api'
import { ResultScreen } from '@/components/ResultScreen'
import { ScarMarker, type ScarMark } from '@/components/ScarMarker'
import { PaymentScreen } from '@/components/PaymentScreen'
import { PhotoUploader } from '@/components/PhotoUploader'
import {
  getHandoffBodyPhoto,
  hasPendingBodyPhoto,
  restorePendingBodyPhotoFromStorage,
  clearHandoffBodyPhoto,
} from '@/lib/pendingPhoto'

const LOG = process.env.NODE_ENV === 'development'
function log(...args: unknown[]) {
  if (LOG) console.log('[FlowWizard]', ...args)
}

const REGION_ONLY_FLOWS: FlowId[] = ['new_to_tattoos', 'from_idea', 'deep_meaning']

export function FlowWizard({ flowId }: { flowId: FlowId }) {
  const config = FLOW_CONFIGS[flowId]
  const [groupIndex, setGroupIndex] = useState(0)
  const [raw, setRaw] = useState<Record<string, string | string[]>>({})
  const [chips, setChips] = useState<string[]>([])
  const [file, setFile] = useState<File | null>(null)
  const [coupleFileA, setCoupleFileA] = useState<File | null>(null)
  const [coupleFileB, setCoupleFileB] = useState<File | null>(null)
  const [referenceFile, setReferenceFile] = useState<File | null>(null)
  const [scarMark, setScarMark] = useState<ScarMark | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<GenerateResponse | null>(null)
  const [showPaywall, setShowPaywall] = useState(false)
  const [credits, setCredits] = useState<number | null>(null)
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState<string>('')
  const [photoRestoring, setPhotoRestoring] = useState(() => hasPendingBodyPhoto())
  const photoRestoreDone = useRef(false)

  const SESSION_KEY = `tattoo-result-${flowId}`

  // Restore persisted result on mount — skip if user is starting fresh with a new photo
  useEffect(() => {
    if (hasPendingBodyPhoto()) {
      log('fresh session with pending photo — step 1, no old result')
      setGroupIndex(0)
      setResult(null)
      return
    }
    try {
      const saved = sessionStorage.getItem(SESSION_KEY)
      if (saved) {
        const parsed = JSON.parse(saved)
        if (parsed?.concepts?.length > 0) {
          log('restoring previous result from session')
          setResult(parsed)
        }
      }
    } catch {}
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Initialise FingerprintJS fingerprint, then load credits
  useEffect(() => {
    initDeviceId().then(() => checkCredits().then(setCredits))
  }, [])

  // Restore body photo — memory handoff first (never destructively consumed)
  useEffect(() => {
    if (config.uploadsInStepsOnly || photoRestoreDone.current) return
    photoRestoreDone.current = true

    const fromMemory = getHandoffBodyPhoto()
    if (fromMemory) {
      log('photo from memory handoff', fromMemory.name)
      setFile(fromMemory)
      setGroupIndex(0)
      setPhotoRestoring(false)
      return
    }

    log('no memory handoff — trying sessionStorage backup')
    restorePendingBodyPhotoFromStorage().then((pending) => {
      if (pending) {
        log('photo from sessionStorage backup', pending.name)
        setFile(pending)
        setGroupIndex(0)
      } else {
        log('no photo found anywhere')
      }
      setPhotoRestoring(false)
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!file) {
      setPhotoPreviewUrl('')
      return
    }
    const url = URL.createObjectURL(file)
    setPhotoPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  const uploadsOnly = config.uploadsInStepsOnly === true
  const hasBodyPhoto = !uploadsOnly && file !== null

  const steps = useMemo(() => {
    let list = getActiveSteps(flowId, hasBodyPhoto, raw)
    const form = String(raw.form || '')
    if (flowId === 'deep_meaning') {
      if (!['script', 'symbol_script'].includes(form)) {
        list = list.filter((x) => x.id !== 'script_quote')
      }
    }
    return list
  }, [flowId, hasBodyPhoto, raw])

  const uiGroups = useMemo((): StepDef[][] => {
    const groups: StepDef[][] = []
    for (let i = 0; i < steps.length; ) {
      if (
        flowId === 'new_to_tattoos' &&
        steps[i].id === 'look' &&
        steps[i + 1]?.id === 'coverage'
      ) {
        groups.push([steps[i], steps[i + 1]])
        i += 2
      } else {
        groups.push([steps[i]])
        i += 1
      }
    }
    return groups
  }, [steps, flowId])

  useEffect(() => {
    setGroupIndex((i) => Math.min(i, Math.max(0, uiGroups.length - 1)))
  }, [uiGroups.length])

  const currentGroup = uiGroups[groupIndex] ?? []
  const isLastGroup = groupIndex >= uiGroups.length - 1

  function stepCanProceed(s: StepDef): boolean {
    if (s.type === 'goal_chips') {
      return Boolean(raw.tattoo_goal) && chips.length >= 1
    }
    if (s.type === 'chips') return chips.length >= 1
    if (s.type === 'file') {
      if (s.id === 'reference_image') {
        if (flowId === 'photo_convert') return referenceFile !== null
        return true
      }
      if (s.id === 'placement_image') {
        if (file === null) return false
        if (flowId === 'scar_coverup' && scarMark === null) return false
        return true
      }
      if (s.id === 'person_a_image') return coupleFileA !== null
      if (s.id === 'person_b_image') return coupleFileB !== null
      return false
    }
    const v = raw[s.id]
    if (s.type === 'text') {
      if (s.id === 'script_quote') {
        const form = String(raw.form || '')
        if (['script', 'symbol_script'].includes(form)) {
          return typeof v === 'string' && v.trim().length > 0
        }
        return true
      }
      if (s.id === 'style_notes' && flowId === 'from_idea') {
        return typeof v === 'string' && v.trim().length >= 3
      }
      if (s.id === 'scar_description') {
        return true
      }
      return typeof v === 'string' && v.trim().length > 2
    }
    return typeof v === 'string' && v.length > 0
  }

  const canNext = useMemo(
    () => currentGroup.length > 0 && currentGroup.every(stepCanProceed),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [currentGroup, raw, chips, file, scarMark, flowId, coupleFileA, coupleFileB, referenceFile]
  )

  function setChoiceFor(stepId: string, value: string) {
    setRaw((prev) => ({ ...prev, [stepId]: value }))
  }

  function toggleChip(value: string) {
    setChips((prev) =>
      prev.includes(value) ? prev.filter((x) => x !== value) : [...prev, value].slice(0, 8)
    )
  }

  function buildAnswers(): FlowAnswers {
    const base: FlowAnswers = {}
    for (const s of steps) {
      if (s.type === 'chips' || s.type === 'goal_chips') continue
      if (s.type === 'file') continue
      const v = raw[s.id]
      if (typeof v === 'string') {
        ;(base as Record<string, string>)[s.id] = v
      }
    }
    if (flowId === 'new_to_tattoos') {
      const look = String(raw.look || 'balanced')
      base.strength = look
      base.priority = 'both'
      base.tattoo_goal = String(raw.tattoo_goal || '')
      base.meaning_chips = chips
      if (hasBodyPhoto) base.body_region = 'from_photo'
    }
    if (flowId === 'from_idea') {
      if (hasBodyPhoto) base.body_region = 'from_photo'
    }
    if (flowId === 'photo_convert') {
      base.style = String(raw.conversion_style || 'minimal')
      base.has_reference_image = Boolean(referenceFile)
      base.body_region = 'from_photo'
    }
    if (flowId === 'deep_meaning') {
      const vis = String(raw.visibility || 'balanced')
      base.strength = vis === 'quiet' ? 'subtle' : vis === 'visible' ? 'bold' : 'balanced'
      if (!base.coverage) base.coverage = vis === 'visible' ? 'large' : 'medium'
      if (hasBodyPhoto) base.body_region = 'from_photo'
    }
    if (flowId === 'scar_coverup') {
      base.body_region = 'from_photo'
      base.scar_strategy = String(raw.scar_strategy || 'camouflage')
      base.scar_type = String(raw.scar_type || '')
      base.scar_description = String(raw.scar_description || '')
      base.coverage = 'medium'
      base.strength = 'bold'
      if (scarMark) {
        base.scar_mark = `${scarMark.cx.toFixed(4)},${scarMark.cy.toFixed(4)},${scarMark.radius.toFixed(4)}`
      }
    }
    if (flowId === 'tattoo_fade') {
      base.fade_strength = (String(raw.fade_strength || 'moderate') as
        | 'subtle'
        | 'moderate'
        | 'heavy')
    }
    if (flowId === 'couple_tattoo') {
      base.couple_mode = String(raw.couple_mode || 'matching_pair') as
        | 'matching_pair'
        | 'complementary_split'
      base.shared_theme = String(raw.shared_theme || '')
      base.shared_style = String(raw.shared_style || 'auto')
      base.shared_coverage = String(raw.shared_coverage || 'medium')
      base.shared_strength = String(raw.shared_strength || 'balanced')
      base.person_a_style = base.shared_style
      base.person_b_style = base.shared_style
      base.person_a_body_region = 'from_photo'
      base.person_b_body_region = 'from_photo'
    }
    return base
  }

  async function runGenerate() {
    if (flowId === 'couple_tattoo') {
      const mode = String(raw.couple_mode || 'matching_pair')
      if (mode !== 'complementary_split' && (!coupleFileA || !coupleFileB)) {
        setError('Upload both partner photos to generate a couple preview.')
        return
      }
    } else if (flowId === 'photo_convert') {
      if (!referenceFile || !file) {
        setError('Upload both a reference photo and your body photo to continue.')
        return
      }
    } else if (flowId === 'scar_coverup' || flowId === 'tattoo_fade') {
      if (!file) {
        setError(
          flowId === 'scar_coverup'
            ? 'Upload a clear photo of the scar on the last step.'
            : 'Upload a clear photo of the tattoo you want to age.'
        )
        return
      }
    } else if (!file) {
      if (!REGION_ONLY_FLOWS.includes(flowId) || !raw.body_region) {
        setError('Upload a body photo or choose a body area to continue.')
        return
      }
    }

    // Check credits before calling API
    if (credits !== null && credits <= 0) {
      setShowPaywall(true)
      return
    }

    setLoading(true)
    setError(null)
    try {
      const answers = buildAnswers()
      const isSplit =
        flowId === 'couple_tattoo' &&
        String(answers.couple_mode || '') === 'complementary_split'
      const isMatchingPair =
        flowId === 'couple_tattoo' && !isSplit && coupleFileA && coupleFileB

      const data =
        isSplit
          ? await generateCoupleTattoos(null, null, answers)
          : isMatchingPair
          ? await generateCoupleTattoos(coupleFileA!, coupleFileB!, answers)
          : await generateTattoos(
              file,
              flowId,
              answers,
              1,
              flowId === 'photo_convert' ? referenceFile : null
            )

      // Update local credits count from response header
      if ((data as any).creditsRemaining !== undefined) {
        setCredits((data as any).creditsRemaining)
      } else if (credits !== null) {
        setCredits(Math.max(0, credits - 1))
      }

      // Persist result so it survives app-switching on mobile
      try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(data)) } catch {}

      setResult(data)
    } catch (e) {
      if ((e as any)?.status === 402) {
        setCredits(0)
        setShowPaywall(true)
        return
      }
      setError(e instanceof Error ? e.message : 'Generation failed')
    } finally {
      setLoading(false)
    }
  }

  if (showPaywall) {
    return <PaymentScreen onBack={() => setShowPaywall(false)} />
  }

  const isSplitMode = flowId === 'couple_tattoo' && String(raw.couple_mode || '') === 'complementary_split'
  const previewBodyPhoto = isSplitMode ? null : flowId === 'couple_tattoo' ? coupleFileA : file
  const designOnlyResult = Boolean(result && !previewBodyPhoto && !isSplitMode)
  if (result && (previewBodyPhoto || isSplitMode || designOnlyResult)) {
    return (
      <ResultScreen
        flowTitle={config.title}
        flowId={flowId}
        data={result}
        bodyPhoto={previewBodyPhoto}
        answers={buildAnswers()}
        referenceImage={flowId === 'photo_convert' ? referenceFile : null}
        couplePhotos={
          flowId === 'couple_tattoo' && coupleFileA && coupleFileB
            ? { a: coupleFileA, b: coupleFileB }
            : undefined
        }
        onBack={() => {
            try { sessionStorage.removeItem(SESSION_KEY) } catch {}
            clearHandoffBodyPhoto()
            setResult(null)
          }}
        onAppendConcepts={(more) => {
            setResult((prev) => {
              const next = prev
                ? { ...prev, concepts: [...prev.concepts, ...more.concepts], replicate_calls: (prev.replicate_calls ?? prev.concepts.length) + (more.replicate_calls ?? more.concepts.length) }
                : more
              try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(next)) } catch {}
              return next
            })
          }}
        onCreditsChange={(c) => setCredits(c)}
      />
    )
  }

  const fileInputClass =
    'block w-full text-sm text-ink-100 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border file:border-border file:bg-ink-800 file:text-ink-100 file:font-medium hover:file:bg-ink-700 cursor-pointer'

  return (
    <div className="max-w-lg mx-auto px-4 pt-5 pb-8 w-full space-y-4">
      <Link href="/" className="text-xs text-ink-100/50 hover:text-ink-100 inline-block">
        ← Home
      </Link>

      <div className="rounded-2xl border border-border/80 bg-gradient-to-b from-ink-900/70 to-ink-950/50 p-5 sm:p-6">
        <div className="flex items-start justify-between gap-3 mb-4">
          <div>
            <h1 className="font-display text-3xl sm:text-4xl text-ink-100 leading-tight">{config.title}</h1>
            <p className="text-ink-100/60 text-sm sm:text-base mt-2 leading-relaxed">{config.description}</p>
          </div>
          {credits !== null && (
            <span className={`text-xs px-2.5 py-1 rounded-full border font-medium shrink-0 ${
              credits <= 0
                ? 'border-red-500/30 bg-red-500/10 text-red-400'
                : 'border-accent/30 bg-accent/10 text-accent'
            }`}>
              {credits <= 0 ? 'No credits' : `${credits} left`}
            </span>
          )}
        </div>

        {flowId === 'new_to_tattoos' && photoRestoring && (
          <div className="rounded-xl border border-border bg-ink-950/70 p-4 flex items-center gap-3">
            <Loader2 className="w-5 h-5 animate-spin text-accent shrink-0" />
            <p className="text-sm text-ink-100/70">Loading your photo…</p>
          </div>
        )}

        {flowId === 'new_to_tattoos' && !photoRestoring && file && photoPreviewUrl && (
          <div className="rounded-xl border border-accent/35 bg-ink-950/70 p-4 flex items-center gap-4">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={photoPreviewUrl}
              alt="Your body photo"
              className="w-24 h-24 sm:w-28 sm:h-28 rounded-xl object-cover border-2 border-accent/30 shrink-0 shadow-lg shadow-black/30"
            />
            <div>
              <p className="text-base sm:text-lg font-semibold text-ink-100">Your body photo</p>
              <p className="text-sm text-accent mt-1 font-medium">Photo uploaded ✓</p>
              <p className="text-xs text-ink-100/45 mt-1">Placement read from your picture</p>
            </div>
          </div>
        )}
      </div>

      {flowId === 'scar_coverup' && raw.scar_type === 'self_harm' && (
        <div className="mb-6 rounded-2xl border border-accent/40 bg-accent/5 p-4">
          <p className="text-sm text-ink-100 font-medium mb-1">
            We see you. This is brave.
          </p>
          <p className="text-sm text-ink-100/70">
            Take your time with these questions. There&apos;s no wrong answer, and
            no rush. If you need someone to talk to right now,{' '}
            <a
              href="https://findahelpline.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent underline-offset-4 hover:underline"
            >
              support is here
            </a>
            .
          </p>
        </div>
      )}

      {!uploadsOnly && !(flowId === 'new_to_tattoos' && file) && (
        <div>
          <PhotoUploader
            value={file}
            onChange={setFile}
            label="Body photo"
            hint={
              (flowId === 'from_idea' || flowId === 'deep_meaning' || flowId === 'new_to_tattoos')
                ? file
                  ? 'Placement will be read from this photo — the "where on the body?" step is skipped.'
                  : 'No photo yet? You will be asked to pick a body area in the steps below.'
                : 'Choose a clear photo of the body area.'
            }
          />
        </div>
      )}

      <div className="text-sm font-semibold text-accent">
        Step {groupIndex + 1} of {uiGroups.length || 1}
      </div>

      {currentGroup.length > 0 && (
        <div className="rounded-2xl border border-border bg-ink-900/80 p-4 sm:p-5">
          {currentGroup.map((subStep, idx) => (
            <div key={subStep.id} className={idx > 0 ? 'mt-5 pt-5 border-t border-border/60' : ''}>
              <h2 className="font-display text-base sm:text-lg text-ink-100 mb-0.5">{subStep.title}</h2>
              {subStep.subtitle && <p className="text-xs text-ink-100/55 mb-3">{subStep.subtitle}</p>}

              {subStep.type === 'goal_chips' && subStep.goalOptions && subStep.chipOptions && (
                <div className="space-y-4">
                  <div>
                    <p className="text-[10px] text-ink-100/45 mb-1.5 uppercase tracking-wide">Direction</p>
                    <div className="grid grid-cols-2 gap-1.5">
                      {subStep.goalOptions.map((o) => (
                        <button
                          key={o.value}
                          type="button"
                          onClick={() => setRaw((p) => ({ ...p, tattoo_goal: o.value }))}
                          className={`rounded-lg border px-3 py-2.5 text-left text-xs sm:text-sm transition ${
                            raw.tattoo_goal === o.value
                              ? 'border-accent bg-accent/10 text-ink-100'
                              : 'border-border bg-ink-950/50 text-ink-100/80'
                          }`}
                        >
                          {o.label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-[10px] text-ink-100/45 mb-1.5 uppercase tracking-wide">
                      Themes — pick at least one
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {subStep.chipOptions.map((o) => (
                        <button
                          key={o.value}
                          type="button"
                          onClick={() => toggleChip(o.value)}
                          className={`rounded-full px-2.5 py-1 text-xs border transition ${
                            chips.includes(o.value)
                              ? 'border-accent bg-accent/15 text-accent'
                              : 'border-border text-ink-100/75'
                          }`}
                        >
                          {o.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {subStep.type === 'text' && (
                <textarea
                  className="w-full rounded-xl bg-ink-950 border border-border px-3 py-2 text-ink-100 placeholder:text-ink-100/35 min-h-[100px]"
                  placeholder={subStep.placeholder}
                  value={typeof raw[subStep.id] === 'string' ? (raw[subStep.id] as string) : ''}
                  onChange={(e) => setRaw((p) => ({ ...p, [subStep.id]: e.target.value }))}
                />
              )}

              {subStep.type === 'choice' && subStep.options && (
                <div className="grid grid-cols-2 gap-1.5">
                  {subStep.options.map((o) => (
                    <button
                      key={o.value}
                      type="button"
                      onClick={() => setChoiceFor(subStep.id, o.value)}
                      className={`rounded-lg border px-3 py-2.5 text-left text-xs sm:text-sm transition ${
                        raw[subStep.id] === o.value
                          ? 'border-accent bg-accent/10 text-ink-100'
                          : 'border-border bg-ink-950/50 text-ink-100/80 hover:border-ink-100/20'
                      }`}
                    >
                      {o.label}
                    </button>
                  ))}
                </div>
              )}

              {subStep.type === 'file' && (
                <div>
                  <PhotoUploader
                    value={
                      subStep.id === 'reference_image' ? referenceFile
                      : subStep.id === 'person_a_image' ? coupleFileA
                      : subStep.id === 'person_b_image' ? coupleFileB
                      : file
                    }
                    onChange={(f) => {
                      if (subStep.id === 'reference_image') setReferenceFile(f)
                      else if (subStep.id === 'person_a_image') setCoupleFileA(f)
                      else if (subStep.id === 'person_b_image') setCoupleFileB(f)
                      else if (subStep.id === 'placement_image') {
                        setFile(f)
                        setScarMark(null)
                      }
                    }}
                    hint={
                      subStep.id === 'placement_image' ? (
                        flowId === 'scar_coverup' ? 'Required — clear photo of the scar area' :
                        flowId === 'tattoo_fade' ? 'Required — clear photo of the tattoo you want to age' :
                        'Required — your skin, where the tattoo goes'
                      ) :
                      subStep.id === 'person_a_image' ? 'Required — Partner A placement photo' :
                      subStep.id === 'person_b_image' ? 'Required — Partner B placement photo' :
                      undefined
                    }
                  />

                  {subStep.id === 'placement_image' && flowId === 'scar_coverup' && file && (
                    <div className="mt-5 pt-5 border-t border-border">
                      <p className="text-sm font-medium text-ink-100 mb-1">
                        Now tap the scar in your photo
                      </p>
                      <p className="text-xs text-ink-100/55 mb-3">
                        This is the most important step — it tells us exactly which area
                        to design around. Drag the circle to fit the scar.
                      </p>
                      <ScarMarker
                        imageFile={file}
                        value={scarMark}
                        onChange={setScarMark}
                      />
                      {!scarMark && (
                        <p className="text-xs text-amber-300/80 mt-2">
                          Tap on the scar to continue.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {error && <p className="text-red-400/90 text-sm">{error}</p>}

      <div className="flex gap-2 pt-1">
        {groupIndex > 0 && (
          <button
            type="button"
            onClick={() => setGroupIndex((i) => Math.max(0, i - 1))}
            className="shrink-0 inline-flex items-center justify-center gap-1 rounded-full border border-border px-4 py-3.5 text-sm text-ink-100/70 touch-manipulation"
          >
            <ChevronLeft className="w-4 h-4" /> Back
          </button>
        )}

        {!isLastGroup ? (
          <button
            type="button"
            disabled={!canNext}
            onClick={() => setGroupIndex((i) => i + 1)}
            className="flex-1 inline-flex items-center justify-center gap-1 rounded-full bg-accent px-5 py-3.5 text-sm font-bold text-ink-950 disabled:opacity-40 shadow-lg shadow-accent/20 animate-cta-pulse touch-manipulation"
          >
            Next step <ChevronRight className="w-4 h-4" />
          </button>
        ) : (
          <button
            type="button"
            disabled={
              !canNext ||
              (flowId === 'couple_tattoo'
                ? String(raw.couple_mode || '') === 'complementary_split'
                  ? false
                  : !coupleFileA || !coupleFileB
                : flowId === 'photo_convert'
                ? !file || !referenceFile
                : flowId === 'scar_coverup' || flowId === 'tattoo_fade'
                ? !file
                : !file && !(REGION_ONLY_FLOWS.includes(flowId) && raw.body_region)) || loading
            }
            onClick={runGenerate}
            className="flex-1 inline-flex items-center justify-center gap-2 rounded-full bg-accent px-5 py-3.5 text-sm font-bold text-ink-950 disabled:opacity-40 shadow-lg shadow-accent/20 animate-cta-pulse touch-manipulation"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            {loading ? 'Generating…' : 'Generate my preview'}
          </button>
        )}
      </div>
    </div>
  )
}
