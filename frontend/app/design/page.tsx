import { redirect } from 'next/navigation'

export const metadata = {
  title: 'Design your tattoo — TattooVisionAI',
}

export default function DesignPage() {
  redirect('/flow/new_to_tattoos')
}
