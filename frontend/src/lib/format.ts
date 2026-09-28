// Display formatting only. Money arrives from the backend as decimal strings and is
// never used for arithmetic here; Number() is used solely to feed Intl for display.

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

const money2 = new Intl.NumberFormat('en-AU', {
  style: 'currency',
  currency: 'AUD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const money4 = new Intl.NumberFormat('en-AU', {
  style: 'currency',
  currency: 'AUD',
  minimumFractionDigits: 4,
  maximumFractionDigits: 4,
})

/** en-AU renders AUD as a bare "$"; force the unambiguous "A$" prefix. */
function withAudPrefix(fmt: Intl.NumberFormat, value: number): string {
  return fmt
    .formatToParts(value)
    .map((p) => (p.type === 'currency' ? 'A$' : p.value))
    .join('')
}

function toNumber(value: string | null | undefined): number | null {
  if (value === null || value === undefined || value.trim() === '') return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

/** "1937.28" -> "A$1,937.28". Returns the fallback for null / unparseable input. */
export function formatMoney(value: string | null | undefined, fallback = '—'): string {
  const n = toNumber(value)
  return n === null ? fallback : withAudPrefix(money2, n)
}

/** "135.4545" -> "A$135.4545" (unit prices keep 4 decimals). */
export function formatUnitPrice(value: string | null | undefined, fallback = '—'): string {
  const n = toNumber(value)
  return n === null ? fallback : withAudPrefix(money4, n)
}

/** "2025-11-30" -> "30 Nov 2025" (no timezone conversion). */
export function formatDate(value: string | null | undefined, fallback = '—'): string {
  if (!value) return fallback
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(value)
  if (!m) return value
  const month = MONTHS[Number(m[2]) - 1]
  if (!month) return value
  return `${Number(m[3])} ${month} ${m[1]}`
}

function clock(h: number, min: number): string {
  const suffix = h >= 12 ? 'pm' : 'am'
  const h12 = h % 12 === 0 ? 12 : h % 12
  return `${h12}:${String(min).padStart(2, '0')} ${suffix}`
}

/**
 * ISO timestamp -> "13 Feb 2025, 11:49 am".
 * Carrier events carry the local time of the depot (either an explicit +hh:mm offset
 * or no offset at all), so those are shown as wall-clock time exactly as reported.
 * UTC ("Z") timestamps, e.g. our own fetched_at, are converted to the viewer's time.
 */
export function formatDateTime(value: string | null | undefined, fallback = '—'): string {
  if (!value) return fallback
  const m = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::\d{2}(?:\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?$/.exec(value)
  if (!m) return value
  const [, y, mo, d, h, mi, zone] = m
  if (zone === 'Z') {
    const dt = new Date(value)
    if (Number.isNaN(dt.getTime())) return value
    return `${dt.getDate()} ${MONTHS[dt.getMonth()]} ${dt.getFullYear()}, ${clock(dt.getHours(), dt.getMinutes())}`
  }
  const month = MONTHS[Number(mo) - 1]
  if (!month) return value
  return `${Number(d)} ${month} ${y}, ${clock(Number(h), Number(mi))}`
}

/** "3 min ago", "2 h ago" etc. Falls back to the absolute time for anything older than a day. */
export function formatRelative(value: string | null | undefined, now = Date.now()): string {
  if (!value) return '—'
  const t = new Date(value).getTime()
  if (Number.isNaN(t)) return formatDateTime(value)
  const secs = Math.round((now - t) / 1000)
  if (secs < 45) return 'just now'
  const mins = Math.round(secs / 60)
  if (mins < 60) return `${mins} min ago`
  const hours = Math.round(mins / 60)
  if (hours < 24) return `${hours} h ago`
  return formatDateTime(value)
}

/** Strip trailing zeros from decimal strings for compact display: "19.0" -> "19". */
function trimDecimal(value: string | number): string {
  const text = String(value)
  return text.includes('.') ? text.replace(/\.?0+$/, '') : text
}

/** Parcel -> "19×19×19 cm, 1.29 kg". */
export function formatParcel(p: {
  length_cm: number | string
  width_cm: number | string
  height_cm: number | string
  weight_kg: string
}): string {
  return `${trimDecimal(p.length_cm)}×${trimDecimal(p.width_cm)}×${trimDecimal(p.height_cm)} cm, ${p.weight_kg} kg`
}

export function carrierName(carrier: string | null | undefined): string {
  switch (carrier) {
    case 'STARTRACK':
      return 'StarTrack'
    case 'TNT':
      return 'TNT'
    case 'UNKNOWN':
    case null:
    case undefined:
      return 'Unknown carrier'
    default:
      return carrier
  }
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`
}
