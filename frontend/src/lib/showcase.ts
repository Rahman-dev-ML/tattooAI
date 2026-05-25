import type { FlowId } from './types'

export type ShowcaseBadge = 'scar' | 'photo'

export interface ShowcaseItem {
  id: string
  label: string
  filterTag: string
  beforeSrc: string
  afterSrc: string
  badge?: ShowcaseBadge
  flowId: FlowId
  hero?: boolean
}

const base = '/showcase'

export const SHOWCASE_ITEMS: ShowcaseItem[] = [
  {
    id: 'arm-blackwork',
    label: 'Male Forearm · Blackwork',
    filterTag: 'Forearm',
    beforeSrc: `${base}/before-arm.jpeg`,
    afterSrc: `${base}/arm-after1.png`,
    flowId: 'from_idea',
    hero: true,
  },
  {
    id: 'arm-japanese-color',
    label: 'Male Forearm · Japanese Color',
    filterTag: 'Forearm',
    beforeSrc: `${base}/before-arm.jpeg`,
    afterSrc: `${base}/arm-after2.png`,
    flowId: 'from_idea',
    hero: true,
  },
  {
    id: 'arm-japanese-female',
    label: 'Female Forearm · Japanese',
    filterTag: 'Forearm',
    beforeSrc: `${base}/sarah-before.jpg`,
    afterSrc: `${base}/sarah-after1.png`,
    flowId: 'from_idea',
    hero: true,
  },
  {
    id: 'scar-hand',
    label: 'Forearm · Scar Cover-up',
    filterTag: 'Scar',
    beforeSrc: `${base}/scar1before.png`,
    afterSrc: `${base}/scar1-after.jpeg`,
    badge: 'scar',
    flowId: 'scar_coverup',
  },
  {
    id: 'photo-cat',
    label: 'Chest · Photo to Tattoo · Blackwork',
    filterTag: 'Photo',
    beforeSrc: `${base}/ali-before.jpeg`,
    afterSrc: `${base}/ali-after.png`,
    badge: 'photo',
    flowId: 'photo_convert',
  },
  {
    id: 'scar-shoulder',
    label: 'Shoulder · Scar Transform',
    filterTag: 'Scar',
    beforeSrc: `${base}/scar2before.webp`,
    afterSrc: `${base}/scar2after.jpeg`,
    badge: 'scar',
    flowId: 'scar_coverup',
  },
  {
    id: 'arm-japanese-female-2',
    label: 'Female Forearm · Japanese',
    filterTag: 'Forearm',
    beforeSrc: `${base}/sarah-before.jpg`,
    afterSrc: `${base}/sarah-after2.png`,
    flowId: 'from_idea',
  },
]

export const SHOWCASE_FILTERS = ['All', 'Forearm', 'Scar', 'Photo'] as const

export type ShowcaseFilter = (typeof SHOWCASE_FILTERS)[number]
