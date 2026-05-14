export type HealingStrategy = 'Camouflage' | 'Transform' | 'Overshadow'

export interface HealingStory {
  id: string
  initial: string
  name: string
  age?: number
  scarType: string
  strategy: HealingStrategy
  quote: string
  story: string
  photoUrl?: string | null
}

export const FALLBACK_HEALING_STORIES: HealingStory[] = [
  {
    id: 's1',
    initial: 'M',
    name: 'Maya',
    age: 28,
    scarType: 'C-section',
    strategy: 'Transform',
    quote: 'My scar used to remind me of fear. Now it is the spine of a flowering vine.',
    story:
      'After two complicated pregnancies I felt disconnected from my body. The transform option made my scar the center of a botanical piece, every flower a small celebration.',
  },
  {
    id: 's2',
    initial: 'D',
    name: 'Darius',
    age: 34,
    scarType: 'Burn (kitchen accident)',
    strategy: 'Camouflage',
    quote: 'For the first time I look in the mirror and do not flinch.',
    story:
      "Eight years of long sleeves. The camouflage approach blended the burn texture into a dense Japanese-inspired wave. My partner cried when we saw the preview.",
  },
  {
    id: 's3',
    initial: 'A',
    name: 'Anonymous',
    scarType: 'Healing journey',
    strategy: 'Transform',
    quote: 'A semicolon, a moth, a quiet promise to keep going.',
    story:
      "I was not ready to walk into a tattoo studio yet. Designing this in private gave me weeks to sit with it. The artist I eventually chose called it the most considered cover-up they had ever inked.",
  },
  {
    id: 's4',
    initial: 'L',
    name: 'Lena',
    age: 41,
    scarType: 'Mastectomy',
    strategy: 'Overshadow',
    quote: 'I was told I would hide forever. I chose a phoenix instead.',
    story:
      'Bilateral mastectomy left two long scars across my chest. The overshadow strategy gave me bold, mythic imagery I now show off at the beach.',
  },
]

