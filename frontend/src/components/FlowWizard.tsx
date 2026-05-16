'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { ChevronLeft, ChevronRight, Loader2 } from 'lucide-react'
import type { FlowAnswers, FlowId, GenerateResponse } from '@/lib/types'
import { FLOW_CONFIGS, getActiveSteps } from '@/lib/flowConfigs'
import { generateCoupleTattoos, generateTattoos, checkCredits, getDeviceId, initDeviceId } from '@/lib/api'
import { ResultScreen } from '@/components/ResultScreen'
import { ScarMarker, type ScarMark } from '@/components/ScarMarker'
import { PaymentScreen } from '@/components/PaymentScreen'

export function FlowWizard({ flowId }: { flowId: FlowId }) {
  const config = FLOW_CONFIGS[flowId]
  const [stepIndex, setStepIndex] = useState(0)
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

  // Initialise FingerprintJS fingerprint, then load credits
  useEffect(() => {
    initDeviceId().then(() => checkCredits().then(setCredits))
  }, [])

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

  useEffect(() => {
    setStepIndex((i) => Math.min(i, Math.max(0, steps.length - 1)))
  }, [steps.length])

  const step = steps[stepIndex]
  const isLast = stepIndex >= steps.length - 1

  const canNext = useMemo(() => {
    if (!step) return false
    if (step.type === 'goal_chips') {
      return Boolean(raw.tattoo_goal) && chips.length >= 1
    }
    if (step.type === 'chips') return chips.length >= 1
    if (step.type === 'file') {
      if (step.id === 'reference_image') return true
      if (step.id === 'placement_image') {
        if (file === null) return false
        if (flowId === 'scar_coverup' && scarMark === null) return false
        return true
      }
      if (step.id === 'person_a_image') return coupleFileA !== null
      if (step.id === 'person_b_image') return coupleFileB !== null
      return false
    }
    const v = raw[step.id]
    if (step.type === 'text') {
      if (step.id === 'script_quote') {
        const form = String(raw.form || '')
        if (['script', 'symbol_script'].includes(form)) {
          return typeof v === 'string' && v.trim().length > 0
        }
        return true
      }
      if (step.id === 'style_notes' && flowId === 'from_idea') {
        return typeof v === 'string' && v.trim().length >= 3
      }
      if (step.id === 'scar_description') {
        return true
      }
      return typeof v === 'string' && v.trim().length > 2
    }
    return typeof v === 'string' && v.length > 0
  }, [step, raw, chips, file, scarMark, flowId, coupleFileA, coupleFileB])

  function setChoice(value: string) {
    if (!step) return
    setRaw((prev) => ({ ...prev, [step.id]: value }))
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
    } else if (flowId === 'photo_convert' || flowId === 'scar_coverup' || flowId === 'tattoo_fade') {
      if (!file) {
        setError(
          flowId === 'scar_coverup'
            ? 'Upload a clear photo of the scar on the last step.'
            : flowId === 'tattoo_fade'
            ? 'Upload a clear photo of the tattoo you want to age.'
            : 'Upload a body photo on the last step (where the tattoo goes).'
        )
        return
      }
    } else if (!file) {
      setError('Upload a body photo first.')
      return
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
              file as File,
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
  if (result && (previewBodyPhoto || isSplitMode)) {
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
        onBack={() => setResult(null)}
        onAppendConcepts={(more) => {
          setResult((prev) => {
            if (!prev) return more
            const offset = prev.concepts.length
            const merged = more.concepts.map((c, i) => ({
              ...c,
              id: `c${offset + i + 1}`,
            }))
            const prevRuns = prev.replicate_calls ?? prev.concepts.length
            const moreRuns = more.replicate_calls ?? more.concepts.length
            return {
              ...prev,
              concepts: [...prev.concepts, ...merged],
              replicate_calls: prevRuns + moreRuns,
            }
          })
        }}
      />
    )
  }

  const fileInputClass =
    'block w-full text-sm text-ink-100 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border file:border-border file:bg-ink-800 file:text-ink-100 file:font-medium hover:file:bg-ink-700 cursor-pointer'

  return (
    <div className="max-w-lg mx-auto px-4 py-10">
      <Link href="/" className="text-sm text-ink-100/50 hover:text-ink-100 mb-6 inline-block">
        ← Home
      </Link>
      <div className="flex items-start justify-between mb-1">
        <h1 className="font-display text-3xl text-ink-100">{config.title}</h1>
        {credits !== null && (
          <span className={`text-xs px-2.5 py-1 rounded-full border font-medium mt-1 ${
            credits <= 0
              ? 'border-red-500/30 bg-red-500/10 text-red-400'
              : 'border-border bg-ink-800 text-ink-100/60'
          }`}>
            {credits <= 0 ? 'No credits' : `${credits} credit${credits === 1 ? '' : 's'} left`}
          </span>
        )}
      </div>
      <p className="text-ink-100/55 text-sm mb-8">{config.description}</p>

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

      {!uploadsOnly && (
        <div className="rounded-2xl border border-border bg-ink-900/60 p-5 mb-6">
          <label className="block text-sm font-medium text-ink-100 mb-2">Body photo</label>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className={fileInputClass}
          />
          <p className="text-sm text-ink-100/70 mt-3">
            {file ? (
              <span className="text-accent/90">Selected: {file.name}</span>
            ) : (
              <span className="text-ink-100/60">Choose a clear photo of the body area.</span>
            )}
          </p>
          {(flowId === 'from_idea' || flowId === 'deep_meaning' || flowId === 'new_to_tattoos') &&
            file && (
              <p className="text-xs text-accent/80 mt-2">
                Placement will be read from this photo — the &quot;where on the body?&quot; step is skipped.
              </p>
            )}
          {(flowId === 'from_idea' || flowId === 'deep_meaning' || flowId === 'new_to_tattoos') &&
            !file && (
              <p className="text-xs text-ink-100/50 mt-2">
                No photo yet? You will be asked to pick a body area in the steps below.
              </p>
            )}
        </div>
      )}

      <div className="mb-2 flex justify-between text-xs text-ink-100/40">
        <span>
          Step {stepIndex + 1} / {steps.length || 1}
        </span>
      </div>

      {step && (
        <div className="rounded-2xl border border-border bg-ink-900/80 p-6 min-h-[180px]">
          <h2 className="font-display text-xl text-ink-100 mb-1">{step.title}</h2>
          {step.subtitle && <p className="text-sm text-ink-100/55 mb-4">{step.subtitle}</p>}

          {step.type === 'goal_chips' && step.goalOptions && step.chipOptions && (
            <div className="space-y-5">
              <div>
                <p className="text-xs text-ink-100/45 mb-2 uppercase tracking-wide">Direction</p>
                <div className="grid gap-2">
                  {step.goalOptions.map((o) => (
                    <button
                      key={o.value}
                      type="button"
                      onClick={() => setRaw((p) => ({ ...p, tattoo_goal: o.value }))}
                      className={`rounded-xl border px-4 py-3 text-left text-sm transition ${
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
                <p className="text-xs text-ink-100/45 mb-2 uppercase tracking-wide">
                  Themes — pick at least one
                </p>
                <div className="flex flex-wrap gap-2">
                  {step.chipOptions.map((o) => (
                    <button
                      key={o.value}
                      type="button"
                      onClick={() => toggleChip(o.value)}
                      className={`rounded-full px-3 py-1.5 text-sm border transition ${
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

          {step.type === 'text' && (
            <textarea
              className="w-full rounded-xl bg-ink-950 border border-border px-3 py-2 text-ink-100 placeholder:text-ink-100/35 min-h-[100px]"
              placeholder={step.placeholder}
              value={typeof raw[step.id] === 'string' ? (raw[step.id] as string) : ''}
              onChange={(e) => setRaw((p) => ({ ...p, [step.id]: e.target.value }))}
            />
          )}

          {step.type === 'choice' && step.options && (
            <div className="grid gap-2">
              {step.options.map((o) => (
                <button
                  key={o.value}
                  type="button"
                  onClick={() => setChoice(o.value)}
                  className={`rounded-xl border px-4 py-3 text-left text-sm transition ${
                    raw[step.id] === o.value
                      ? 'border-accent bg-accent/10 text-ink-100'
                      : 'border-border bg-ink-950/50 text-ink-100/80 hover:border-ink-100/20'
                  }`}
                >
                  {o.label}
                </button>
              ))}
            </div>
          )}

          {step.type === 'file' && (
            <div>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => {
                  const f = e.target.files?.[0] ?? null
                  if (step.id === 'reference_image') setReferenceFile(f)
                  else if (step.id === 'person_a_image') setCoupleFileA(f)
                  else if (step.id === 'person_b_image') setCoupleFileB(f)
                  else if (step.id === 'placement_image') {
                    setFile(f)
                    setScarMark(null)
                  }
                }}
                className={fileInputClass}
              />
              <p className="text-sm text-ink-100/70 mt-3">
                {step.id === 'reference_image' &&
                  (referenceFile ? (
                    <span className="text-accent/90">Selected: {referenceFile.name}</span>
                  ) : (
                    <span className="text-ink-100/60">Optional — add a reference image</span>
                  ))}
                {step.id === 'placement_image' &&
                  (file ? (
                    <span className="text-accent/90">Selected: {file.name}</span>
                  ) : (
                    <span className="text-ink-100/60">
                      {flowId === 'scar_coverup'
                        ? 'Required — clear photo of the scar area'
                        : flowId === 'tattoo_fade'
                        ? 'Required — clear photo of the tattoo you want to age'
                        : 'Required — your skin, where the tattoo goes'}
                    </span>
                  ))}
                {step.id === 'person_a_image' &&
                  (coupleFileA ? (
                    <span className="text-accent/90">Selected: {coupleFileA.name}</span>
                  ) : (
                    <span className="text-ink-100/60">Required — Partner A placement photo</span>
                  ))}
                {step.id === 'person_b_image' &&
                  (coupleFileB ? (
                    <span className="text-accent/90">Selected: {coupleFileB.name}</span>
                  ) : (
                    <span className="text-ink-100/60">Required — Partner B placement photo</span>
                  ))}
              </p>

              {step.id === 'placement_image' && flowId === 'scar_coverup' && file && (
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
      )}

      {error && <p className="text-red-400/90 text-sm mt-4">{error}</p>}

      <div className="flex justify-between mt-8">
        <button
          type="button"
          disabled={stepIndex === 0}
          onClick={() => setStepIndex((i) => Math.max(0, i - 1))}
          className="inline-flex items-center gap-1 text-sm text-ink-100/60 disabled:opacity-30"
        >
          <ChevronLeft className="w-4 h-4" /> Back
        </button>

        {!isLast ? (
          <button
            type="button"
            disabled={!canNext}
            onClick={() => setStepIndex((i) => i + 1)}
            className="inline-flex items-center gap-1 rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-ink-950 disabled:opacity-40"
          >
            Next <ChevronRight className="w-4 h-4" />
          </button>
        ) : (
          <button
            type="button"
            disabled={
              (flowId === 'couple_tattoo'
                ? String(raw.couple_mode || '') === 'complementary_split'
                  ? false
                  : !coupleFileA || !coupleFileB
                : !file) || loading
            }
            onClick={runGenerate}
            className="inline-flex items-center gap-2 rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-ink-950 disabled:opacity-40"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            {loading ? 'Generating…' : 'Generate preview'}
          </button>
        )}
      </div>
    </div>
  )
}
