import { useId, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { lookupTracking, USE_MOCKS } from '../api/client'
import type { ApiError } from '../api/client'
import type { LookupCarrier, Tracking } from '../api/types'
import { Spinner } from '../components/Feedback'
import { TrackingCard, TrackingCardSkeleton } from '../components/TrackingCard'
import { toApiError } from '../lib/useAsync'

const MAX_IDS = 10

/** Split on commas, whitespace and newlines; drop blanks and duplicates, keep order. */
function parseIds(input: string): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const part of input.split(/[\s,;]+/)) {
    const id = part.trim()
    if (!id) continue
    const key = id.toUpperCase()
    if (seen.has(key)) continue
    seen.add(key)
    out.push(id)
  }
  return out
}

export function TrackingLookupPage() {
  const [carrier, setCarrier] = useState<LookupCarrier>('STARTRACK')
  const [text, setText] = useState('')
  const [results, setResults] = useState<Tracking[] | null>(null)
  const [pendingCount, setPendingCount] = useState(0)
  const [error, setError] = useState<ApiError | null>(null)
  const [loading, setLoading] = useState(false)
  const runId = useRef(0)
  const carrierId = useId()
  const idsId = useId()
  const hintId = useId()

  const ids = parseIds(text)
  const tooMany = ids.length > MAX_IDS
  const canSubmit = ids.length > 0 && !tooMany && !loading

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    const id = ++runId.current
    setLoading(true)
    setError(null)
    setPendingCount(ids.length)
    lookupTracking(carrier, ids)
      .then((res) => {
        if (id === runId.current) setResults(res)
      })
      .catch((err: unknown) => {
        if (id === runId.current) {
          setError(toApiError(err))
          setResults(null)
        }
      })
      .finally(() => {
        if (id === runId.current) setLoading(false)
      })
  }

  return (
    <div className="page">
      <header className="page-head">
        <h1>Track a parcel</h1>
        <p className="page-head__sub">
          Look up StarTrack or TNT consignments directly, without opening an order.
        </p>
      </header>

      <form className="lookup" onSubmit={onSubmit} noValidate>
        <div className="lookup__field lookup__field--carrier">
          <label htmlFor={carrierId}>Carrier</label>
          <select id={carrierId} value={carrier} onChange={(e) => setCarrier(e.target.value as LookupCarrier)}>
            <option value="STARTRACK">StarTrack (Australia Post)</option>
            <option value="TNT">TNT</option>
          </select>
        </div>
        <div className="lookup__field lookup__field--ids">
          <label htmlFor={idsId}>Tracking numbers</label>
          <textarea
            id={idsId}
            rows={4}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={carrier === 'TNT' ? '305506914' : '2FWZ50008569, RBXZ50016112'}
            aria-describedby={hintId}
            aria-invalid={tooMany}
            spellCheck={false}
            autoCapitalize="characters"
          />
          <p id={hintId} className={tooMany ? 'lookup__hint is-error' : 'lookup__hint'}>
            {tooMany
              ? `${ids.length} numbers entered. Look up at most ${MAX_IDS} at a time.`
              : `Separate numbers with commas or new lines. ${ids.length} of ${MAX_IDS}.`}
          </p>
          {USE_MOCKS ? (
            <p className="lookup__hint">
              Sample data: try <span className="code">FAIL123</span> (carrier error), <span className="code">LEGACY1</span>{' '}
              (unsupported) or any TNT number other than <span className="code">305506914</span> (not found).
            </p>
          ) : null}
        </div>
        <div className="lookup__actions">
          <button type="submit" className="btn btn--primary" disabled={!canSubmit}>
            {loading ? <Spinner label="Looking up" /> : null}
            {loading ? 'Looking up…' : 'Look up tracking'}
          </button>
        </div>
      </form>

      <section aria-live="polite" aria-busy={loading} className="lookup__results">
        {loading ? (
          <div className="tcards">
            {Array.from({ length: Math.min(pendingCount, 3) }, (_, i) => (
              <TrackingCardSkeleton key={i} />
            ))}
          </div>
        ) : error ? (
          <div className="inline-error" role="alert">
            <p>{error.isNetwork ? 'The tracking service could not be reached.' : 'The lookup failed.'} {error.message}</p>
          </div>
        ) : results ? (
          results.length === 0 ? (
            <p className="empty">No results came back for these numbers.</p>
          ) : (
            <>
              <h2 className="section-title">
                {results.length} {results.length === 1 ? 'result' : 'results'}
              </h2>
              <div className="tcards">
                {results.map((t, i) => (
                  <TrackingCard key={`${t.tracking_no}-${i}`} tracking={t} />
                ))}
              </div>
            </>
          )
        ) : null}
      </section>
    </div>
  )
}
