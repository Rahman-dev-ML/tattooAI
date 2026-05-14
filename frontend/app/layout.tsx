import type { Metadata } from 'next'
import { Crimson_Pro, DM_Sans } from 'next/font/google'
import './globals.css'

const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-geist-sans',
})

const crimson = Crimson_Pro({
  subsets: ['latin'],
  weight: ['400', '600'],
  variable: '--font-display',
})

export const metadata: Metadata = {
  title: 'Tattoo Advisor — Preview before you commit',
  description:
    'AI tattoo ideas with virtual body preview, fit guidance, and compare — visual planning only, not medical advice.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${dmSans.variable} ${crimson.variable}`}>
      <body className="font-sans">{children}</body>
    </html>
  )
}
