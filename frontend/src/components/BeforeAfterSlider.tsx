'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

interface BeforeAfterSliderProps {
  beforeSrc: string
  afterSrc: string
  beforeLabel?: string
  afterLabel?: string
}

export function BeforeAfterSlider({
  beforeSrc,
  afterSrc,
  beforeLabel = 'Before',
  afterLabel = 'After',
}: BeforeAfterSliderProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState(0)
  const [isDragging, setIsDragging] = useState(false)
  const [showHint, setShowHint] = useState(true)

  useEffect(() => {
    const t = setTimeout(() => setShowHint(false), 4000)
    return () => clearTimeout(t)
  }, [])

  const updateFromX = useCallback((clientX: number) => {
    const el = containerRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const pct = ((clientX - rect.left) / rect.width) * 100
    setPosition(Math.max(0, Math.min(100, pct)))
    setShowHint(false)
  }, [])

  const onStart = useCallback(
    (clientX: number) => {
      setIsDragging(true)
      updateFromX(clientX)
    },
    [updateFromX]
  )

  const onMove = useCallback(
    (clientX: number) => {
      if (isDragging) updateFromX(clientX)
    },
    [isDragging, updateFromX]
  )

  const onEnd = useCallback(() => setIsDragging(false), [])

  return (
    <div
      ref={containerRef}
      className="relative w-full select-none overflow-hidden rounded-2xl border border-border bg-black/40 touch-none"
      style={{ aspectRatio: '1 / 1', maxHeight: '65vh' }}
      onMouseDown={(e) => onStart(e.clientX)}
      onMouseMove={(e) => onMove(e.clientX)}
      onMouseUp={onEnd}
      onMouseLeave={onEnd}
      onTouchStart={(e) => {
        e.preventDefault()
        const t = e.touches[0]
        if (t) onStart(t.clientX)
      }}
      onTouchMove={(e) => {
        e.preventDefault()
        const t = e.touches[0]
        if (t) onMove(t.clientX)
      }}
      onTouchEnd={onEnd}
      draggable={false}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={beforeSrc}
        alt={beforeLabel}
        className="absolute inset-0 w-full h-full object-contain pointer-events-none"
        draggable={false}
      />

      <div
        className="absolute inset-0 pointer-events-none"
        style={{ clipPath: `inset(0 ${100 - position}% 0 0)` }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={afterSrc}
          alt={afterLabel}
          className="absolute inset-0 w-full h-full object-contain"
          draggable={false}
        />
      </div>

      {/* beforeLabel is always on the LEFT (the base photo, revealed at position=0) */}
      <span className="absolute top-3 left-3 px-3 py-1.5 rounded-xl text-[11px] font-semibold uppercase tracking-wider z-10 bg-black/70 text-ink-100/90 backdrop-blur-sm">
        {beforeLabel}
      </span>
      {/* afterLabel is always on the RIGHT (the tattoo, revealed by sliding right) */}
      <span className="absolute top-3 right-3 px-3 py-1.5 rounded-xl text-[11px] font-semibold uppercase tracking-wider z-10 bg-accent text-ink-950">
        {afterLabel}
      </span>

      <div
        className="absolute top-0 bottom-0 w-0.5 pointer-events-none z-20 bg-accent shadow-[0_0_18px_rgba(255,255,255,0.4)]"
        style={{ left: `calc(${position}% - 1px)` }}
      >
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-11 h-11 rounded-full grid place-items-center bg-accent text-ink-950 shadow-lg border-[3px] border-white/90 cursor-ew-resize">
          <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
            <path
              d="M7 4l-4 6 4 6M13 4l4 6-4 6"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      </div>

      {showHint && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 px-4 py-1.5 rounded-full text-xs font-semibold z-30 animate-bounce flex items-center gap-2 bg-accent text-ink-950 shadow-lg pointer-events-none">
          <svg width="12" height="12" viewBox="0 0 14 14" fill="none">
            <path
              d="M4 2l-3 5 3 5M10 2l3 5-3 5"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          Slide right to reveal tattoo
        </div>
      )}
    </div>
  )
}
