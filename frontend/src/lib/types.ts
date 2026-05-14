export type FlowId =
  | 'new_to_tattoos'
  | 'from_idea'
  | 'photo_convert'
  | 'deep_meaning'
  | 'scar_coverup'
  | 'couple_tattoo'
  | 'tattoo_fade'

export interface FlowAnswers {
  body_region?: string
  coverage?: string
  style?: string
  strength?: string
  look?: string
  idea?: string
  tattoo_goal?: string
  priority?: string
  meaning_chips?: string[]
  conversion_style?: string
  photo_subject?: string
  meaning_theme?: string
  expression?: string
  form?: string
  visibility?: string
  style_notes?: string
  script_quote?: string
  has_reference_image?: boolean
  scar_strategy?: string
  scar_type?: string
  scar_shape?: string
  scar_description?: string
  scar_intent?: string
  scar_mark?: string
  couple_mode?: 'matching_pair' | 'complementary_split'
  shared_theme?: string
  shared_style?: string
  shared_coverage?: string
  shared_strength?: string
  person_a_style?: string
  person_b_style?: string
  person_a_body_region?: string
  person_b_body_region?: string
  couple_pair_id?: string
  fade_strength?: 'subtle' | 'moderate' | 'heavy'
}

export interface FitFactor {
  key: string
  label: string
  value: number
}

export interface FitResult {
  score: number
  summary: string
  factors: FitFactor[]
}

export interface ConceptResult {
  id: string
  variant_index: number
  image_base64: string
  media_type: string
  style_label: string
  coverage_label: string
  explanation: string
  /** Per-card advisory fit % */
  advisory_score?: number
}

export interface GenerateResponse {
  flow_id: string
  concepts: ConceptResult[]
  fit: FitResult
  disclaimer: string
  replicate_calls?: number
  couple?: {
    pair_id: string
    mode: string
    left_image_base64: string
    right_image_base64: string
    pair_image_base64: string
    media_type: string
  }
}

export interface SavedConcept {
  savedAt: string
  flowId: FlowId
  flowTitle: string
  concept: ConceptResult
  fitScore: number
  previewDataUrl: string
}
