'use client'

import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import type { ShowcaseItem } from '@/lib/showcase'
import { ShowcaseCompare } from './ShowcaseCompare'

export function ShowcaseCard({
  item,
  showTryLink = false,
}: {
  item: ShowcaseItem
  showTryLink?: boolean
}) {
  return (
    <div className="rounded-2xl border border-border/80 bg-ink-900/50 overflow-hidden group">
      <div className="relative">
        {item.badge === 'scar' && (
          <span className="absolute top-3 left-3 z-20 px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider bg-black/70 text-accent border border-accent/30">
            Scar
          </span>
        )}
        {item.badge === 'photo' && (
          <span className="absolute top-3 left-3 z-20 px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider bg-accent text-ink-950">
            Photo → AI Tattoo
          </span>
        )}
        <ShowcaseCompare beforeSrc={item.beforeSrc} afterSrc={item.afterSrc} />
      </div>
      <div className="flex items-center justify-between gap-2 px-4 py-3 border-t border-border/60">
        <p className="text-xs text-ink-100/55 truncate">{item.label}</p>
        {showTryLink && (
          <Link
            href={`/flow/${item.flowId}`}
            className="text-xs font-medium text-accent hover:text-accent/80 shrink-0 inline-flex items-center gap-0.5"
          >
            Try it <ArrowRight className="w-3 h-3" />
          </Link>
        )}
      </div>
    </div>
  )
}
