type Tone = 'green' | 'blue' | 'amber' | 'red' | 'grey'

function toneFor(status: string): Tone {
  const s = status.trim().toLowerCase()
  if (['completed', 'delivered', 'delivered in full', 'fulfilled', 'ok'].includes(s)) return 'green'
  if (s.includes('transit') || s.includes('shipped') || s.includes('dispatched')) return 'blue'
  if (s.includes('process') || s.includes('pending') || s.includes('hold')) return 'amber'
  if (s.includes('cancel') || s.includes('fail') || s.includes('reject')) return 'red'
  return 'grey'
}

export function StatusBadge({ status, tone }: { status: string | null | undefined; tone?: Tone }) {
  const label = status?.trim() || 'Unknown'
  return <span className={`badge badge--${tone ?? toneFor(label)}`}>{label}</span>
}
