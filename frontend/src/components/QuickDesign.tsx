'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Loader2 } from 'lucide-react'
import { generateTattoos, checkCredits, initDeviceId } from '@/lib/api'
import type { GenerateResponse } from '@/lib/types'
import { PhotoUploader } from '@/components/PhotoUploader'
import { ResultScreen } from '@/components/ResultScreen'
import { PaymentScreen } from '@/components/PaymentScreen'

const SESSION_KEY = 'tattoo-result-quick_design'

export function QuickDesign() {
  const [prompt, setPrompt] = useState('')
  const [photo, setPhoto] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<GenerateResponse | null>(null)
  const [showPaywall, setShowPaywall] = useState(false)
  const [credits, setCredits] = useState<number | null>(null)

  // Restore persisted result on mount
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(SESSION_KEY)
      if (saved) {
        const parsed = JSON.parse(saved)
        if (parsed?.concepts?.length > 0) setResult(parsed)
      }
    } catch {}
    initDeviceId().then(() => checkCredits().then(setCredits))
  }, [])

  async function handleGenerate() {
    if (!photo || !prompt.trim()) return

    if (credits !== null && credits <= 0) {
      setShowPaywall(true)
      return
    }

    setLoading(true)
    setError(null)
    try {
      const data = await generateTattoos(photo, 'from_idea', { idea: prompt.trim() }, 1, null)

      if ((data as any).creditsRemaining !== undefined) {
        setCredits((data as any).creditsRemaining)
      } else if (credits !== null) {
        setCredits(Math.max(0, credits - 1))
      }

      try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(data)) } catch {}
      setResult(data)
    } catch (e) {
      if ((e as any)?.status === 402) {
        setCredits(0)
        setShowPaywall(true)
        return
      }
      setError(e instanceof Error ? e.message : 'Generation failed — please try again')
    } finally {
      setLoading(false)
    }
  }

  if (showPaywall) {
    return <PaymentScreen onBack={() => setShowPaywall(false)} />
  }

  if (result) {
    return (
      <ResultScreen
        flowTitle="Quick Design"
        flowId="from_idea"
        data={result}
        bodyPhoto={photo}
        answers={{ idea: prompt.trim() }}
        onBack={() => {
          try { sessionStorage.removeItem(SESSION_KEY) } catch {}
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

  const canGenerate = !!photo && prompt.trim().length > 0 && !loading

  return (
    <div className="max-w-lg mx-auto px-4 py-10">
      <Link href="/" className="inline-flex items-center gap-1 text-sm text-ink-100/50 hover:text-ink-100/80 mb-8">
        ← Home
      </Link>

      <div className="mb-8">
        <h1 className="font-display text-3xl text-ink-100 mb-2">Design your tattoo</h1>
        <p className="text-ink-100/55 text-sm">
          Describe what you want — anything from &quot;a small rose on my wrist&quot; to &quot;something meaningful about strength&quot;. Upload a photo of the body area and we&apos;ll generate a preview.
        </p>
      </div>

      {/* Credits badge */}
      {credits !== null && (
        <div className="mb-6 flex justify-end">
          <span className={`text-xs px-2.5 py-1 rounded-full border font-medium ${
            credits <= 0
              ? 'border-red-500/30 bg-red-500/10 text-red-400'
              : 'border-border bg-ink-800 text-ink-100/60'
          }`}>
            {credits <= 0 ? 'No credits' : `${credits} credit${credits === 1 ? '' : 's'} left`}
          </span>
        </div>
      )}

      {/* Prompt */}
      <div className="mb-5">
        <label className="block text-sm font-medium text-ink-100 mb-2">
          What do you want? <span className="text-red-400">*</span>
        </label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g. a phoenix rising from flames, small and fine-line on my forearm… or just 'something about new beginnings'"
          rows={3}
          maxLength={400}
          className="w-full rounded-xl border border-border bg-ink-900/60 px-4 py-3 text-sm text-ink-100 placeholder:text-ink-100/30 focus:outline-none focus:border-accent/50 resize-none"
        />
        <p className="text-xs text-ink-100/30 mt-1 text-right">{prompt.length}/400</p>
      </div>

      {/* Photo upload */}
      <div className="mb-7">
        <PhotoUploader
          value={photo}
          onChange={setPhoto}
          label={<>Body photo <span className="text-red-400">*</span></>}
          hint="Take a photo or upload one showing the area where you want the tattoo."
        />
      </div>

      {error && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 mb-5 text-sm text-red-400">
          {error}
        </div>
      )}

      <button
        type="button"
        onClick={handleGenerate}
        disabled={!canGenerate}
        className="w-full inline-flex items-center justify-center gap-2 rounded-full bg-accent px-6 py-3.5 text-base font-medium text-ink-950 disabled:opacity-40 transition active:scale-95"
      >
        {loading ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Generating your design…
          </>
        ) : (
          'Generate preview'
        )}
      </button>

      {loading && (
        <p className="text-center text-xs text-ink-100/40 mt-3">
          This usually takes 30–60 seconds
        </p>
      )}
    </div>
  )
}
