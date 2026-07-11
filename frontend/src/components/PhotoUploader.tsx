'use client'

import { useId } from 'react'
import type React from 'react'
import { Camera, ImageIcon, X } from 'lucide-react'

interface PhotoUploaderProps {
  value: File | null
  onChange: (file: File | null) => void
  label?: React.ReactNode
  hint?: string
  compact?: boolean
}

export function PhotoUploader({ value, onChange, label, hint, compact }: PhotoUploaderProps) {
  const galleryId = useId()
  const cameraId = useId()

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    onChange(e.target.files?.[0] ?? null)
    e.target.value = ''
  }

  if (value) {
    return (
      <div className={`rounded-2xl border border-accent/30 bg-ink-900/60 ${compact ? 'p-3' : 'p-4'}`}>
        {label && <p className={`font-medium text-ink-100 ${compact ? 'text-xs mb-2' : 'text-sm mb-3'}`}>{label}</p>}
        <div className="flex items-center gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={URL.createObjectURL(value)}
            alt="Selected"
            className={`rounded-xl object-cover border border-border shrink-0 ${compact ? 'w-12 h-12' : 'w-16 h-16'}`}
          />
          <div className="flex-1 min-w-0">
            <p className="text-sm text-accent/90 font-medium truncate">{value.name}</p>
            <p className="text-xs text-ink-100/50 mt-0.5">
              {(value.size / 1024).toFixed(0)} KB
            </p>
          </div>
          <button
            type="button"
            onClick={() => onChange(null)}
            className="p-2 rounded-full hover:bg-ink-800 text-ink-100/40 hover:text-ink-100/80 shrink-0 touch-manipulation"
            aria-label="Remove photo"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className={`rounded-2xl border border-border bg-ink-900/60 ${compact ? 'p-3' : 'p-4'}`}>
      {label && <p className={`font-medium text-ink-100 ${compact ? 'text-xs mb-2' : 'text-sm mb-3'}`}>{label}</p>}

      <div className="grid grid-cols-2 gap-2 sm:gap-3">
        <label
          htmlFor={galleryId}
          className={`flex flex-col items-center justify-center gap-1 rounded-xl border border-border bg-ink-800/60 text-sm text-ink-100/80 hover:border-accent/40 hover:bg-ink-800 transition active:scale-95 cursor-pointer touch-manipulation ${
            compact ? 'px-2 py-3' : 'px-3 py-5 gap-2'
          }`}
        >
          <ImageIcon className={`text-accent ${compact ? 'w-5 h-5' : 'w-6 h-6'}`} />
          <span className={`font-medium ${compact ? 'text-xs' : ''}`}>Upload Photo</span>
          {!compact && <span className="text-xs text-ink-100/40">From gallery</span>}
        </label>

        <label
          htmlFor={cameraId}
          className={`flex flex-col items-center justify-center gap-1 rounded-xl border border-border bg-ink-800/60 text-sm text-ink-100/80 hover:border-accent/40 hover:bg-ink-800 transition active:scale-95 cursor-pointer touch-manipulation ${
            compact ? 'px-2 py-3' : 'px-3 py-5 gap-2'
          }`}
        >
          <Camera className={`text-accent ${compact ? 'w-5 h-5' : 'w-6 h-6'}`} />
          <span className={`font-medium ${compact ? 'text-xs' : ''}`}>Take Photo</span>
          {!compact && <span className="text-xs text-ink-100/40">Open camera</span>}
        </label>
      </div>

      {hint && <p className={`text-ink-100/50 mt-2 ${compact ? 'text-[11px] leading-snug' : 'text-xs mt-3'}`}>{hint}</p>}

      <input
        id={galleryId}
        type="file"
        accept="image/*"
        className="sr-only"
        onChange={handleFile}
      />
      <input
        id={cameraId}
        type="file"
        accept="image/*"
        capture="environment"
        className="sr-only"
        onChange={handleFile}
      />
    </div>
  )
}
