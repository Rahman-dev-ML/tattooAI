'use client'

import { useEffect, useMemo, useRef, useState } from 'react'

export interface ScarMark {
  cx: number
  cy: number
  radius: number
}

interface ScarMarkerProps {
  imageFile: File
  value: ScarMark | null
  onChange: (mark: ScarMark | null) => void
}

const DEFAULT_RADIUS = 0.16

export function ScarMarker({ imageFile, value, onChange }: ScarMarkerProps) {
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [imgSize, setImgSize] = useState<{ w: number; h: number } | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [dragMode, setDragMode] = useState<'move' | 'resize' | null>(null)

  useEffect(() => {
    const url = URL.createObjectURL(imageFile)
    setImageUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [imageFile])

  function handleImgLoad(e: React.SyntheticEvent<HTMLImageElement>) {
    const el = e.currentTarget
    setImgSize({ w: el.naturalWidth, h: el.naturalHeight })
  }

  const aspect = useMemo(() => {
    if (!imgSize) return '1 / 1'
    return `${imgSize.w} / ${imgSize.h}`
  }, [imgSize])

  function clampedXY(clientX: number, clientY: number) {
    const el = containerRef.current
    if (!el) return null
    const rect = el.getBoundingClientRect()
    const x = (clientX - rect.left) / rect.width
    const y = (clientY - rect.top) / rect.height
    return {
      x: Math.max(0, Math.min(1, x)),
      y: Math.max(0, Math.min(1, y)),
      width: rect.width,
      height: rect.height,
    }
  }

  function placeMark(clientX: number, clientY: number) {
    const p = clampedXY(clientX, clientY)
    if (!p) return
    onChange({
      cx: p.x,
      cy: p.y,
      radius: value?.radius ?? DEFAULT_RADIUS,
    })
  }

  function resizeMark(clientX: number, clientY: number) {
    const p = clampedXY(clientX, clientY)
    if (!p || !value) return
    const dx = (p.x - value.cx) * (p.width / Math.min(p.width, p.height))
    const dy = (p.y - value.cy) * (p.height / Math.min(p.width, p.height))
    const r = Math.max(0.03, Math.min(0.5, Math.sqrt(dx * dx + dy * dy)))
    onChange({ ...value, radius: r })
  }

  useEffect(() => {
    if (!dragMode) return

    function onMove(e: MouseEvent | TouchEvent) {
      const t = 'touches' in e ? e.touches[0] : (e as MouseEvent)
      if (!t) return
      if (dragMode === 'move') placeMark(t.clientX, t.clientY)
      else resizeMark(t.clientX, t.clientY)
      if ('touches' in e) e.preventDefault()
    }
    function onUp() {
      setDragMode(null)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    window.addEventListener('touchmove', onMove, { passive: false })
    window.addEventListener('touchend', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
      window.removeEventListener('touchmove', onMove)
      window.removeEventListener('touchend', onUp)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dragMode, value?.cx, value?.cy, value?.radius])

  // Compute circle position/size as percentages of the container.
  // Container has the same aspect ratio as the image, so 1 unit of
  // container width == imgSize.w in image pixels (and similarly for height).
  const circleStyle = useMemo(() => {
    if (!value || !imgSize) return null
    const shortSide = Math.min(imgSize.w, imgSize.h)
    const widthPct = ((value.radius * 2 * shortSide) / imgSize.w) * 100
    const heightPct = ((value.radius * 2 * shortSide) / imgSize.h) * 100
    return {
      left: `${value.cx * 100}%`,
      top: `${value.cy * 100}%`,
      width: `${widthPct}%`,
      height: `${heightPct}%`,
    }
  }, [value, imgSize])

  return (
    <div className="space-y-3">
      <div
        ref={containerRef}
        className="relative w-full overflow-hidden rounded-2xl border border-border bg-black/40 select-none touch-none"
        style={{ aspectRatio: aspect }}
        onMouseDown={(e) => {
          setDragMode('move')
          placeMark(e.clientX, e.clientY)
        }}
        onTouchStart={(e) => {
          const t = e.touches[0]
          if (!t) return
          e.preventDefault()
          setDragMode('move')
          placeMark(t.clientX, t.clientY)
        }}
      >
        {imageUrl && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={imageUrl}
            alt="Mark the scar"
            onLoad={handleImgLoad}
            className="absolute inset-0 w-full h-full object-contain pointer-events-none"
            draggable={false}
          />
        )}

        {value && circleStyle && (
          <div
            className="absolute"
            style={{
              left: circleStyle.left,
              top: circleStyle.top,
              width: circleStyle.width,
              height: circleStyle.height,
              transform: 'translate(-50%, -50%)',
            }}
          >
            <div
              aria-hidden
              className="absolute inset-0 pointer-events-none rounded-full border-2 border-accent"
              style={{
                background:
                  'radial-gradient(circle, rgba(255,200,80,0.18) 0%, rgba(255,200,80,0.10) 70%, transparent 100%)',
                boxShadow: '0 0 12px rgba(255,200,80,0.35)',
              }}
            />
            <button
              type="button"
              aria-label="Resize scar mark"
              onMouseDown={(e) => {
                e.stopPropagation()
                setDragMode('resize')
              }}
              onTouchStart={(e) => {
                e.stopPropagation()
                e.preventDefault()
                setDragMode('resize')
              }}
              className="absolute bottom-0 right-0 w-5 h-5 rounded-full bg-accent border-2 border-white cursor-nwse-resize"
              style={{ transform: 'translate(50%, 50%)' }}
            />
          </div>
        )}

        {!value && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <span className="rounded-full bg-black/70 px-4 py-2 text-xs font-medium text-ink-100/90">
              Tap on the scar
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-ink-100/55">
          {value
            ? 'Drag the circle to reposition. Drag the handle to resize.'
            : 'Tap directly on the scar in your photo.'}
        </p>
        {value && (
          <button
            type="button"
            onClick={() => onChange(null)}
            className="text-xs text-ink-100/60 hover:text-ink-100 underline-offset-2 hover:underline"
          >
            Clear
          </button>
        )}
      </div>
    </div>
  )
}
