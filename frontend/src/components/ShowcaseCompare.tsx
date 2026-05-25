'use client'

interface ShowcaseCompareProps {
  beforeSrc: string
  afterSrc: string
  className?: string
}

/** Static before/after split — no slider interaction (matches marketing mockups). */
export function ShowcaseCompare({ beforeSrc, afterSrc, className = '' }: ShowcaseCompareProps) {
  return (
    <div
      className={`relative w-full overflow-hidden bg-black/60 ${className}`}
      style={{ aspectRatio: '4 / 3' }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={beforeSrc}
        alt="Before"
        className="absolute inset-0 w-full h-full object-cover"
        draggable={false}
      />
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ clipPath: 'inset(0 0 0 50%)' }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={afterSrc}
          alt="AI preview"
          className="absolute inset-0 w-full h-full object-cover"
          draggable={false}
        />
      </div>

      <span className="absolute bottom-3 left-3 px-2.5 py-1 rounded-md text-[10px] font-semibold uppercase tracking-wider z-10 bg-black/75 text-white/90">
        Before
      </span>
      <span className="absolute bottom-3 right-3 px-2.5 py-1 rounded-md text-[10px] font-semibold uppercase tracking-wider z-10 bg-accent text-ink-950">
        AI Preview
      </span>

      <div
        className="absolute top-0 bottom-0 left-1/2 w-0.5 -translate-x-1/2 bg-accent/90 z-10 pointer-events-none"
        aria-hidden
      />
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-9 h-9 rounded-full grid place-items-center bg-accent text-ink-950 shadow-lg border-2 border-white/90 z-10 pointer-events-none"
        aria-hidden
      >
        <svg width="14" height="14" viewBox="0 0 20 20" fill="none">
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
  )
}
