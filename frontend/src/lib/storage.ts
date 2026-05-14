import type { SavedConcept } from './types'

const KEY = 'tattoo-advisor-saves'

export function loadSaves(): SavedConcept[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as SavedConcept[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function saveConcept(entry: SavedConcept): void {
  const prev = loadSaves()
  const next = [entry, ...prev].slice(0, 24)
  localStorage.setItem(KEY, JSON.stringify(next))
}

export function removeSave(savedAt: string): void {
  const prev = loadSaves()
  localStorage.setItem(
    KEY,
    JSON.stringify(prev.filter((s) => s.savedAt !== savedAt))
  )
}
