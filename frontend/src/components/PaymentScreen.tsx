'use client'

import { useState } from 'react'
import { Loader2, Lock, Zap, CheckCircle2 } from 'lucide-react'
import { initiatePayment, redirectToPayFast } from '@/lib/api'

interface PaymentScreenProps {
  onBack: () => void
}

export function PaymentScreen({ onBack }: PaymentScreenProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handlePay = async () => {
    setError('')
    setLoading(true)
    try {
      const session = await initiatePayment()
      redirectToPayFast(session.checkout_url, session.form_data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Could not start payment')
      setLoading(false)
    }
  }

  return (
    <div className="max-w-lg mx-auto px-4 py-10">
      <button
        onClick={onBack}
        className="text-sm text-ink-100/50 hover:text-ink-100 mb-6 inline-flex items-center gap-1"
      >
        ← Back
      </button>

      <div className="rounded-3xl border border-border bg-ink-900 p-8">
        {/* Icon */}
        <div className="w-14 h-14 rounded-2xl bg-accent/10 border border-accent/20 flex items-center justify-center mb-6">
          <Zap className="w-7 h-7 text-accent" />
        </div>

        <h2 className="font-display text-2xl text-ink-100 mb-1">
          Free previews used up
        </h2>
        <p className="text-ink-100/55 text-sm mb-8">
          You&apos;ve used your 2 free generations. Get 5 more concepts for $1.
        </p>

        {/* Price */}
        <div className="rounded-2xl border border-border bg-ink-800 p-5 mb-6 text-center">
          <div className="text-4xl font-bold text-ink-100 mb-0.5">
            $1 <span className="text-xl text-ink-100/55">USD</span>
          </div>
          <div className="text-xs text-ink-100/40">One-time · No subscription · No account needed</div>
        </div>

        {/* Features */}
        <ul className="space-y-3 mb-8">
          {[
            '5 AI-generated tattoo concepts',
            'All flows — cover-up, fade, couple & more',
            'Pay securely via Visa or Mastercard',
          ].map((text) => (
            <li key={text} className="flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-accent shrink-0 mt-0.5" />
              <span className="text-sm text-ink-100/80">{text}</span>
            </li>
          ))}
        </ul>

        {error && (
          <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 mb-4 text-sm text-red-400">
            {error}
          </div>
        )}

        <button
          onClick={handlePay}
          disabled={loading}
          className="w-full py-4 rounded-2xl bg-accent text-white font-semibold text-base 
                     hover:bg-accent/90 active:scale-[0.98] transition-all disabled:opacity-60
                     flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Connecting to payment…
            </>
          ) : (
            'Pay $1 — Get 5 concepts'
          )}
        </button>

        <div className="mt-4 flex items-center justify-center gap-1.5 text-ink-100/30 text-xs">
          <Lock className="w-3 h-3" />
          Secured · Visa &amp; Mastercard accepted
        </div>
      </div>
    </div>
  )
}
