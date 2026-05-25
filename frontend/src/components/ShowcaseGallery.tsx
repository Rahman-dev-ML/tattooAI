'use client'

import { useMemo, useState } from 'react'
import { SHOWCASE_ITEMS } from '@/lib/showcase'
import { ShowcaseCard } from './ShowcaseCard'

export function ShowcaseGallery({ heroOnly = false }: { heroOnly?: boolean }) {
  const [filter, setFilter] = useState<string>('All')

  const items = useMemo(() => {
    let list = heroOnly
      ? SHOWCASE_ITEMS.filter((i) => i.hero)
      : SHOWCASE_ITEMS.filter((i) => !i.hero)
    if (filter !== 'All' && !heroOnly) {
      list = list.filter((i) => i.id === filter)
    }
    return list
  }, [filter, heroOnly])

  if (heroOnly) {
    return (
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map((item) => (
          <ShowcaseCard key={item.id} item={item} />
        ))}
      </div>
    )
  }

  const labelChips = SHOWCASE_ITEMS.filter((i) => !i.hero)

  return (
    <section className="mb-20">
      <div className="flex gap-2 mb-5 overflow-x-auto pb-1 scrollbar-none">
        <button
          type="button"
          onClick={() => setFilter('All')}
          className={`shrink-0 rounded-lg px-3 py-2 text-xs font-medium transition border ${
            filter === 'All'
              ? 'border-accent/50 bg-accent/10 text-accent'
              : 'border-border/80 bg-ink-900/60 text-ink-100/50 hover:text-ink-100/80'
          }`}
        >
          All examples
        </button>
        {labelChips.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setFilter(item.id)}
            className={`shrink-0 rounded-lg px-3 py-2 text-xs font-medium transition border whitespace-nowrap ${
              filter === item.id
                ? 'border-accent/50 bg-accent/10 text-accent'
                : 'border-border/80 bg-ink-900/60 text-ink-100/50 hover:text-ink-100/80'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div className="grid sm:grid-cols-2 gap-4">
        {items.map((item) => (
          <ShowcaseCard key={item.id} item={item} showTryLink />
        ))}
      </div>
    </section>
  )
}
