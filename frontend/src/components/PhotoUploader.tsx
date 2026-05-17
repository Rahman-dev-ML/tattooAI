'use client'

import { useRef } from 'react'
import { Camera, ImageIcon, X } from 'lucide-react'

interface PhotoUploaderProps {
  value: File | null
  onChange: (file: File | null) => void
  label?: string
  hint?: string
}

export function PhotoUploader({ value, onChange, label, hint }: PhotoUploaderProps) {
  const cameraRef = useRef<HTMLInputElement>(null)
  const galleryRef = useRef<HTMLInputElement>(null)

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    onChange(e.target.files?.[0] ?? null)
    // Reset so the same file can be re-selected after clearing
    e.target.value = ''
  }

  if (value) {
    return (
      <div className="rounded-2xl border border-accent/30 bg-ink-900/60 p-4">
        {label && <p className="text-sm font-medium text-ink-100 mb-3">{label}</p>}
        <div className="flex items-center gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={URL.createObjectURL(value)}
            alt="Selected"
            className="w-16 h-16 rounded-xl object-cover border border-border shrink-0"
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
            className="p-2 rounded-full hover:bg-ink-800 text-ink-100/40 hover:text-ink-100/80 shrink-0"
            aria-label="Remove photo"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-2xl border border-border bg-ink-900/60 p-4">
      {label && <p className="text-sm font-medium text-ink-100 mb-3">{label}</p>}

      <div className="grid grid-cols-2 gap-3">
        {/* Take Photo — opens camera directly on mobile */}
        <button
          type="button"
          onClick={() => cameraRef.current?.click()}
          className="flex flex-col items-center justify-center gap-2 rounded-xl border border-border bg-ink-800/60 px-3 py-5 text-sm text-ink-100/80 hover:border-accent/40 hover:bg-ink-800 transition active:scale-95"
        >
          <Camera className="w-6 h-6 text-accent" />
          <span className="font-medium">Take Photo</span>
          <span className="text-xs text-ink-100/40">Open camera</span>
        </button>

        {/* Choose from gallery */}
        <button
          type="button"
          onClick={() => galleryRef.current?.click()}
          className="flex flex-col items-center justify-center gap-2 rounded-xl border border-border bg-ink-800/60 px-3 py-5 text-sm text-ink-100/80 hover:border-accent/40 hover:bg-ink-800 transition active:scale-95"
        >
          <ImageIcon className="w-6 h-6 text-ink-100/60" />
          <span className="font-medium">Upload Photo</span>
          <span className="text-xs text-ink-100/40">From gallery</span>
        </button>
      </div>

      {hint && <p className="text-xs text-ink-100/50 mt-3">{hint}</p>}

      {/* Hidden inputs */}
      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleFile}
      />
      <input
        ref={galleryRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFile}
      />
    </div>
  )
}
