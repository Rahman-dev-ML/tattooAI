import type { FlowId } from './types'

export type StepType =
  | 'choice'
  | 'text'
  | 'chips'
  | 'file'
  | 'goal_chips'

export interface StepDef {
  id: string
  title: string
  subtitle?: string
  type: StepType
  options?: { value: string; label: string }[]
  /** For type goal_chips — direction choices */
  goalOptions?: { value: string; label: string }[]
  /** For type goal_chips — theme chips */
  chipOptions?: { value: string; label: string }[]
  placeholder?: string
  multiline?: boolean
}

export interface FlowConfig {
  id: FlowId
  title: string
  description: string
  steps: StepDef[]
  /** If true, do not show the top-of-page body upload (flow uses per-step uploads). */
  uploadsInStepsOnly?: boolean
}

const BODY_REGIONS = [
  { value: 'forearm', label: 'Forearm' },
  { value: 'upper_arm', label: 'Upper arm' },
  { value: 'shoulder', label: 'Shoulder' },
  { value: 'wrist', label: 'Wrist' },
  { value: 'hand_back', label: 'Back of hand' },
  { value: 'calf', label: 'Calf' },
  { value: 'thigh', label: 'Thigh' },
  { value: 'chest', label: 'Chest' },
  { value: 'upper_back', label: 'Upper back' },
  { value: 'ribs', label: 'Ribs / side' },
  { value: 'ankle', label: 'Ankle' },
  { value: 'neck', label: 'Neck' },
  { value: 'other', label: 'Other / best fit' },
]

const STYLES = [
  { value: 'auto', label: 'Auto (choose for me)' },
  { value: 'minimalist', label: 'Minimalist' },
  { value: 'fine_line', label: 'Fine line' },
  { value: 'blackwork', label: 'Blackwork' },
  { value: 'traditional', label: 'Traditional' },
  { value: 'script', label: 'Script' },
  { value: 'geometric', label: 'Geometric' },
  { value: 'ornamental', label: 'Ornamental' },
  { value: 'japanese', label: 'Japanese-inspired' },
  { value: 'realism', label: 'Realism' },
]

const COVERAGE = [
  { value: 'small', label: 'Small' },
  { value: 'medium', label: 'Medium' },
  { value: 'large', label: 'Large' },
  { value: 'unsure', label: 'Not sure' },
]

const STRENGTH = [
  { value: 'subtle', label: 'Subtle' },
  { value: 'balanced', label: 'Balanced' },
  { value: 'bold', label: 'Bold' },
]

const MEANING_CHIPS = [
  'Strength',
  'Faith',
  'Patience',
  'Rebirth',
  'Healing',
  'Love',
  'Family',
  'Discipline',
  'Freedom',
  'Hope',
  'Peace',
  'Loss',
]

export const FLOW_CONFIGS: Record<FlowId, FlowConfig> = {
  new_to_tattoos: {
    id: 'new_to_tattoos',
    title: 'New to tattoos',
    description: 'A short path — direction, themes, then your photo.',
    steps: [
      {
        id: 'goal_chips',
        title: 'Direction & themes',
        subtitle: 'Pick one direction and at least one theme — we blend them into the design.',
        type: 'goal_chips',
        goalOptions: [
          { value: 'meaningful', label: 'Meaningful' },
          { value: 'aesthetic', label: 'Aesthetic' },
          { value: 'bold_statement', label: 'Bold statement' },
          { value: 'unsure', label: 'Not sure' },
        ],
        chipOptions: MEANING_CHIPS.map((m) => ({ value: m.toLowerCase(), label: m })),
      },
      {
        id: 'body_region',
        title: 'Where on the body?',
        subtitle: 'Only if you have not uploaded a body photo yet — otherwise we read placement from your picture.',
        type: 'choice',
        options: BODY_REGIONS,
      },
      {
        id: 'look',
        title: 'What look do you prefer?',
        type: 'choice',
        options: [
          { value: 'subtle', label: 'Subtle' },
          { value: 'balanced', label: 'Balanced' },
          { value: 'bold', label: 'Bold' },
        ],
      },
      {
        id: 'coverage',
        title: 'How much coverage?',
        type: 'choice',
        options: COVERAGE,
      },
    ],
  },
  from_idea: {
    id: 'from_idea',
    title: 'Generate from my idea',
    description: 'Describe your idea, pick a style, then put it in your own words for the prompt.',
    steps: [
      {
        id: 'idea',
        title: 'What is your idea?',
        type: 'text',
        placeholder: 'e.g. geometric wolf, memorial dates, botanical sleeve fragment…',
        multiline: true,
      },
      {
        id: 'style',
        title: 'Which style?',
        type: 'choice',
        options: STYLES,
      },
      {
        id: 'style_notes',
        title: 'Describe how you want this style to look',
        subtitle: 'Required — this text is sent straight into the AI prompt (mood, line weight, references, what to avoid).',
        type: 'text',
        placeholder:
          'e.g. crisp single-weight outline, soft whip shading only under the rose, no dot-fill, classy not tribal…',
        multiline: true,
      },
      {
        id: 'body_region',
        title: 'Where do you want it?',
        subtitle:
          'Only if you did not upload a body photo above — with a photo we read placement from your picture.',
        type: 'choice',
        options: BODY_REGIONS,
      },
      {
        id: 'strength',
        title: 'How strong should it look?',
        type: 'choice',
        options: STRENGTH,
      },
      {
        id: 'coverage',
        title: 'How much coverage?',
        type: 'choice',
        options: COVERAGE,
      },
    ],
  },
  photo_convert: {
    id: 'photo_convert',
    title: 'Convert photo into tattoo',
    description: 'Reference and choices first — then upload your body so we can show the ink on your skin.',
    uploadsInStepsOnly: true,
    steps: [
      {
        id: 'reference_image',
        title: 'Reference image (optional)',
        subtitle: 'Pet, sketch, symbol — helps lock the subject. Skip if you will describe it in text only.',
        type: 'file',
      },
      {
        id: 'photo_subject',
        title: 'What should we translate?',
        type: 'text',
        placeholder: 'e.g. my dog from the reference, rose, tribal sketch…',
        multiline: true,
      },
      {
        id: 'conversion_style',
        title: 'Conversion style',
        type: 'choice',
        options: [
          { value: 'fine_line', label: 'Fine line' },
          { value: 'blackwork', label: 'Blackwork' },
          { value: 'minimal', label: 'Minimal' },
          { value: 'stencil', label: 'Stencil style' },
          { value: 'realistic', label: 'Realistic' },
          { value: 'geometric', label: 'Geometric interpretation' },
          { value: 'ornamental', label: 'Ornamental interpretation' },
        ],
      },
      {
        id: 'strength',
        title: 'How strong should it look?',
        type: 'choice',
        options: STRENGTH,
      },
      {
        id: 'coverage',
        title: 'How much coverage?',
        type: 'choice',
        options: COVERAGE,
      },
      {
        id: 'placement_image',
        title: 'Your body — see the tattoo here',
        subtitle:
          'Upload a clear photo of the exact skin area where you want this. We composite the design onto this shot.',
        type: 'file',
      },
    ],
  },
  deep_meaning: {
    id: 'deep_meaning',
    title: 'Deep meaning tattoo',
    description: 'Values and symbolism — add lettering if you want script.',
    steps: [
      {
        id: 'meaning_theme',
        title: 'What kind of meaning?',
        type: 'choice',
        options: [
          { value: 'strength', label: 'Strength' },
          { value: 'faith', label: 'Faith' },
          { value: 'patience', label: 'Patience' },
          { value: 'love', label: 'Love' },
          { value: 'family', label: 'Family' },
          { value: 'loss', label: 'Loss' },
          { value: 'healing', label: 'Healing' },
          { value: 'rebirth', label: 'Rebirth' },
          { value: 'discipline', label: 'Discipline' },
          { value: 'freedom', label: 'Freedom' },
          { value: 'hope', label: 'Hope' },
          { value: 'philosophy', label: 'Philosophy' },
        ],
      },
      {
        id: 'expression',
        title: 'What kind of expression?',
        type: 'choice',
        options: [
          { value: 'deep_symbolic', label: 'Deep and symbolic' },
          { value: 'elegant_subtle', label: 'Elegant and subtle' },
          { value: 'bold_powerful', label: 'Bold and powerful' },
          { value: 'poetic', label: 'Poetic' },
          { value: 'spiritual', label: 'Spiritual' },
        ],
      },
      {
        id: 'form',
        title: 'Preferred form',
        type: 'choice',
        options: [
          { value: 'symbol', label: 'Symbol' },
          { value: 'script', label: 'Script or quote' },
          { value: 'symbol_script', label: 'Symbol + script' },
          { value: 'abstract', label: 'Abstract' },
          { value: 'ai_decide', label: 'Let AI propose' },
        ],
      },
      {
        id: 'script_quote',
        title: 'Script, name, or quote',
        subtitle: 'Required for “Script” or “Symbol + script”. Type the exact words you want in the design.',
        type: 'text',
        placeholder: 'e.g. a name, a short quote, a date, or a line in any language…',
        multiline: true,
      },
      {
        id: 'body_region',
        title: 'Where?',
        subtitle: 'Skip if your photo already shows the area.',
        type: 'choice',
        options: BODY_REGIONS,
      },
      {
        id: 'visibility',
        title: 'How visible should it feel?',
        type: 'choice',
        options: [
          { value: 'quiet', label: 'Quiet / personal' },
          { value: 'balanced', label: 'Balanced' },
          { value: 'visible', label: 'Clearly visible' },
        ],
      },
    ],
  },
  scar_coverup: {
    id: 'scar_coverup',
    title: 'Cover up a scar',
    description:
      'Transform a scar into beautiful art. We craft a tattoo that camouflages, transforms, or overshadows the scar — designed for healing.',
    uploadsInStepsOnly: true,
    steps: [
      {
        id: 'placement_image',
        title: 'Upload your photo & mark the scar',
        subtitle:
          'A well-lit shot of the scar area. After uploading, tap directly on the scar so we know exactly where to design around.',
        type: 'file',
      },
      {
        id: 'scar_strategy',
        title: 'How should we handle the scar?',
        subtitle: 'Three approaches — pick what fits your feeling.',
        type: 'choice',
        options: [
          {
            value: 'camouflage',
            label: 'Camouflage — blend it into dense art',
          },
          {
            value: 'transform',
            label: 'Transform — make the scar part of the design',
          },
          {
            value: 'overshadow',
            label: 'Overshadow — bold tattoo dominates the eye',
          },
        ],
      },
      {
        id: 'scar_type',
        title: 'What type of scar?',
        subtitle: 'Helps us pick the right artistic approach.',
        type: 'choice',
        options: [
          { value: 'surgical', label: 'Surgical / incision' },
          { value: 'injury', label: 'Injury / accident' },
          { value: 'burn', label: 'Burn' },
          { value: 'stretch_marks', label: 'Stretch marks' },
          { value: 'cesarean', label: 'C-section' },
          { value: 'mastectomy', label: 'Mastectomy' },
          { value: 'self_harm', label: 'Healing journey (we’ve got you)' },
          { value: 'other', label: 'Other' },
        ],
      },
      {
        id: 'style',
        title: 'Tattoo style',
        type: 'choice',
        options: STYLES,
      },
      {
        id: 'scar_description',
        title: 'Anything else we should know? (optional)',
        subtitle:
          'Shape, length, age, texture, or feelings about it — helps us design with intention.',
        type: 'text',
        placeholder:
          'e.g. 8cm raised line on left forearm, 2 years old, want something with movement…',
        multiline: true,
      },
    ],
  },
  tattoo_fade: {
    id: 'tattoo_fade',
    title: 'Faded tattoo',
    description: 'Upload a tattoo photo and see how it would look after years of natural fade.',
    uploadsInStepsOnly: true,
    steps: [
      {
        id: 'placement_image',
        title: 'Upload your tattoo photo',
        subtitle:
          'A clear, well-lit photo of the tattoo you want to age. Existing tattoo or one of our previews — both work.',
        type: 'file',
      },
      {
        id: 'fade_strength',
        title: 'How much fade?',
        subtitle: 'Roughly how many years of skin wear should we simulate?',
        type: 'choice',
        options: [
          { value: 'subtle', label: 'Subtle — 2 to 3 years' },
          { value: 'moderate', label: 'Moderate — 5 to 7 years' },
          { value: 'heavy', label: 'Heavy — 10 to 15 years' },
        ],
      },
    ],
  },
  couple_tattoo: {
    id: 'couple_tattoo',
    title: 'Couple tattoo',
    description: 'Matching pair or complementary split, generated for both partners together.',
    uploadsInStepsOnly: true,
    steps: [
      {
        id: 'couple_mode',
        title: 'Choose couple mode',
        subtitle: 'Matching pair = same design DNA. Complementary split = two halves that complete together.',
        type: 'choice',
        options: [
          { value: 'matching_pair', label: 'Matching pair' },
          { value: 'complementary_split', label: 'Complementary split' },
        ],
      },
      {
        id: 'shared_theme',
        title: 'Shared story or symbol',
        subtitle: 'What should connect both tattoos?',
        type: 'text',
        placeholder: 'e.g. moon + tide, growth after chaos, two cranes, lock & key energy…',
        multiline: true,
      },
      {
        id: 'shared_coverage',
        title: 'Shared coverage',
        type: 'choice',
        options: COVERAGE,
      },
      {
        id: 'shared_strength',
        title: 'Shared intensity',
        type: 'choice',
        options: STRENGTH,
      },
      {
        id: 'shared_style',
        title: 'Tattoo style',
        subtitle: 'One shared style for both partners.',
        type: 'choice',
        options: STYLES,
      },
      {
        id: 'person_a_body_part',
        title: 'Partner A — body part',
        subtitle: 'Where will Partner A wear the tattoo?',
        type: 'choice',
        options: [
          { value: 'forearm', label: 'Forearm' },
          { value: 'inner_forearm', label: 'Inner forearm' },
          { value: 'wrist', label: 'Wrist' },
          { value: 'upper_arm', label: 'Upper arm / bicep' },
          { value: 'shoulder', label: 'Shoulder' },
          { value: 'hand', label: 'Hand' },
          { value: 'calf', label: 'Calf' },
          { value: 'thigh', label: 'Thigh' },
          { value: 'ribs', label: 'Ribs' },
          { value: 'back', label: 'Back / shoulder blade' },
          { value: 'chest', label: 'Chest' },
          { value: 'ankle', label: 'Ankle' },
        ],
      },
      {
        id: 'person_b_body_part',
        title: 'Partner B — body part',
        subtitle: 'Where will Partner B wear the tattoo?',
        type: 'choice',
        options: [
          { value: 'forearm', label: 'Forearm' },
          { value: 'inner_forearm', label: 'Inner forearm' },
          { value: 'wrist', label: 'Wrist' },
          { value: 'upper_arm', label: 'Upper arm / bicep' },
          { value: 'shoulder', label: 'Shoulder' },
          { value: 'hand', label: 'Hand' },
          { value: 'calf', label: 'Calf' },
          { value: 'thigh', label: 'Thigh' },
          { value: 'ribs', label: 'Ribs' },
          { value: 'back', label: 'Back / shoulder blade' },
          { value: 'chest', label: 'Chest' },
          { value: 'ankle', label: 'Ankle' },
        ],
      },
      {
        id: 'person_a_image',
        title: 'Partner A photo',
        subtitle: 'Upload a clear body-area photo for Partner A. (Matching pair only.)',
        type: 'file',
      },
      {
        id: 'person_b_image',
        title: 'Partner B photo',
        subtitle: 'Upload a clear body-area photo for Partner B.',
        type: 'file',
      },
    ],
  },
}

export const HOME_FLOW_ORDER: { id: FlowId; label: string; description: string }[] = [
  { id: 'new_to_tattoos', label: 'New to tattoos', description: 'Guided discovery' },
  { id: 'from_idea', label: 'Generate from my idea', description: 'You already have a concept' },
  { id: 'photo_convert', label: 'Convert photo into tattoo', description: 'Pet, portrait, object' },
  { id: 'deep_meaning', label: 'Deep meaning tattoo', description: 'Values & symbolism' },
  { id: 'scar_coverup', label: 'Cover up a scar', description: 'Transform scars into beautiful art' },
  { id: 'couple_tattoo', label: 'Couple tattoo', description: 'Matching pair or complementary split' },
  { id: 'tattoo_fade', label: 'Faded tattoo', description: 'See how a tattoo will age over the years' },
]

/** Steps visible for this moment (e.g. skip body_region when user already has a body photo). */
export function getActiveSteps(
  flowId: FlowId,
  hasBodyPhoto: boolean,
  answers?: Record<string, unknown>
): StepDef[] {
  const cfg = FLOW_CONFIGS[flowId]
  let steps = [...cfg.steps]
  if (flowId === 'new_to_tattoos' && hasBodyPhoto) {
    steps = steps.filter((s) => s.id !== 'body_region')
  }
  if (flowId === 'from_idea' && hasBodyPhoto) {
    steps = steps.filter((s) => s.id !== 'body_region')
  }
  if (flowId === 'deep_meaning' && hasBodyPhoto) {
    steps = steps.filter((s) => s.id !== 'body_region')
  }
  // Couple flow:
  //   complementary_split → no photos AND no body parts (we render two
  //     halves of one design on neutral skin canvases — the only path
  //     that reliably ships true "halves").
  //   matching_pair → photos required, no body-part picks (placement is
  //     read from each photo).
  if (flowId === 'couple_tattoo') {
    const mode = answers?.couple_mode
    if (mode === 'complementary_split') {
      steps = steps.filter(
        (s) =>
          s.id !== 'person_a_image' &&
          s.id !== 'person_b_image' &&
          s.id !== 'person_a_body_part' &&
          s.id !== 'person_b_body_part'
      )
    } else {
      steps = steps.filter(
        (s) =>
          s.id !== 'person_a_body_part' && s.id !== 'person_b_body_part'
      )
    }
  }
  return steps
}
