'use client'

import type { ReactNode } from 'react'

/** Full-width page wrapper — prevents horizontal overflow on mobile. */
export function PageShell({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div className={`w-full min-w-0 overflow-x-clip ${className}`}>
      {children}
    </div>
  )
}
