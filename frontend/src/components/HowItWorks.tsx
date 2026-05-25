import { Eye, Upload, Wand2 } from 'lucide-react'

const STEPS = [
  {
    num: '01',
    icon: Upload,
    title: 'Upload or pick a body area',
    description: 'Take or upload a photo — or just pick a region if you prefer.',
  },
  {
    num: '02',
    icon: Wand2,
    title: 'Answer 3–4 short questions',
    description: 'Style, meaning, placement. No experience needed.',
  },
  {
    num: '03',
    icon: Eye,
    title: 'See the tattoo on your body',
    description: 'AI places a realistic preview on your photo. Save, compare, share.',
  },
]

export function HowItWorks() {
  return (
    <section className="mb-20 pt-4 border-t border-border/40">
      <p className="text-accent text-xs font-semibold tracking-[0.2em] uppercase mb-3">
        Simple process
      </p>
      <h2 className="font-display text-3xl md:text-4xl text-ink-100 mb-2">How it works</h2>
      <p className="text-ink-100/55 text-sm md:text-base max-w-xl mb-10">
        Upload a photo or pick a body area, answer a few questions, and see your design on skin.
      </p>

      <div className="grid md:grid-cols-3 gap-8 md:gap-6">
        {STEPS.map((step) => (
          <div key={step.num} className="relative">
            <span className="font-display text-5xl text-ink-100/[0.07] leading-none select-none">
              {step.num}
            </span>
            <div className="mt-2 mb-4 w-10 h-10 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center">
              <step.icon className="w-5 h-5 text-accent" />
            </div>
            <h3 className="text-base font-semibold text-ink-100 mb-2">{step.title}</h3>
            <p className="text-sm text-ink-100/50 leading-relaxed">{step.description}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
