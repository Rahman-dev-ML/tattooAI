'use client'

import { useCallback, useRef, useState } from 'react'

interface ShowcaseSliderProps {
  beforeSrc: string
  afterSrc: string
  initialPosition?: number
  className?: string
}

export function ShowcaseSlider({
  beforeSrc,
  afterSrc,
  initialPosition = 42,
  className = '',
}: ShowcaseSliderProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState(initialPosition)
  const [isDragging, setIsDragging] = useState(false)

  const updateFromX = useCallback((clientX: number) => {
    const el = containerRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const pct = ((clientX - rect.left) / rect.width) * 100
    setPosition(Math.max(0, Math.min(100, pct)))
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
      className={`relative w-full select-none overflow-hidden bg-black/60 touch-none ${className}`}
      style={{ aspectRatio: '4 / 3' }}
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
        alt="Before"
        className="absolute inset-0 w-full h-full object-cover pointer-events-none"
        draggable={false}
      />

      <div
        className="absolute inset-0 pointer-events-none"
        style={{ clipPath: `inset(0 ${100 - position}% 0 0)` }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={afterSrc}
          alt="AI preview"
          className="absolute inset-0 w-full h-full object-cover"
          draggable={false}
        />
      </div>

      <span className="absolute bottom-3 left-3 px-2.5 py-1 rounded-md text-[10px] font-semibold uppercase tracking-wider z-10 bg-black/75 text-white/90 backdrop-blur-sm">
        Before
      </span>
      <span className="absolute bottom-3 right-3 px-2.5 py-1 rounded-md text-[10px] font-semibold uppercase tracking-wider z-10 bg-accent text-ink-950">
        AI Preview
      </span>

      <div
        className="absolute top-0 bottom-0 w-0.5 pointer-events-none z-20 bg-accent/90"
        style={{ left: `calc(${position}% - 1px)` }}
      >
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-9 h-9 rounded-full grid place-items-center bg-accent text-ink-950 shadow-lg border-2 border-white/90 cursor-ew-resize">
          <svg width="14" height="14" viewBox="0 0 20 20" fill="none" aria-hidden>
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
    </div>
  )
}
