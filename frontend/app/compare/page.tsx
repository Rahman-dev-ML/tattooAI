'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { Trash2 } from 'lucide-react'
import type { SavedConcept } from '@/lib/types'
import { loadSaves, removeSave } from '@/lib/storage'

export default function ComparePage() {
  const [saves, setSaves] = useState<SavedConcept[]>([])

  useEffect(() => {
    setSaves(loadSaves())
  }, [])

  return (
    <div className="max-w-6xl mx-auto px-4 py-10">
      <Link href="/" className="text-sm text-ink-100/50 hover:text-ink-100 mb-6 inline-block">
        ← Home
      </Link>
      <h1 className="font-display text-3xl text-ink-100 mb-2">Compare saved concepts</h1>
      <p className="text-ink-100/55 text-sm mb-8">Stored in this browser only.</p>

      {saves.length === 0 ? (
        <p className="text-ink-100/45">Nothing saved yet. Generate a design and tap Save concept.</p>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {saves.map((s) => (
            <div
              key={s.savedAt}
              className="rounded-2xl border border-border bg-ink-900/60 overflow-hidden"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={s.previewDataUrl} alt="" className="w-full h-40 object-cover" />
              <div className="p-4">
                <p className="text-sm font-medium text-ink-100">{s.flowTitle}</p>
                <p className="text-xs text-accent/90 mt-1">Fit {s.fitScore}</p>
                <p className="text-xs text-ink-100/50 mt-2 line-clamp-2">{s.concept.explanation}</p>
                <button
                  type="button"
                  onClick={() => {
                    removeSave(s.savedAt)
                    setSaves(loadSaves())
                  }}
                  className="mt-3 text-xs text-red-400/80 inline-flex items-center gap-1 hover:underline"
                >
                  <Trash2 className="w-3 h-3" /> Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
