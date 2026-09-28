import { useCallback, useEffect, useRef, useState } from 'react'
import { getOrderTracking } from '../api/client'
import type { ApiError } from '../api/client'
import type { OrderTracking } from '../api/types'
import { toApiError } from '../lib/useAsync'
import { Spinner } from './Feedback'
import { TrackingCard, TrackingCardSkeleton } from './TrackingCard'

/**
 * Loads tracking independently of the order, so the order page never waits on carriers.
 */
export function TrackingPanel({ orderNo, shipmentCount }: { orderNo: string; shipmentCount: number }) {
  const [data, setData] = useState<OrderTracking | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const runId = useRef(0)

  const load = useCallback(
    (refresh: boolean) => {
      const id = ++runId.current
      if (refresh) setRefreshing(true)
      else setLoading(true)
      setError(null)
      getOrderTracking(orderNo, refresh)
        .then((res) => {
          if (id === runId.current) setData(res)
        })
        .catch((err: unknown) => {
          if (id === runId.current) setError(toApiError(err))
        })
        .finally(() => {
          if (id === runId.current) {
            setLoading(false)
            setRefreshing(false)
          }
        })
    },
    [orderNo],
  )

  useEffect(() => {
    load(false)
  }, [load])

  const busy = loading || refreshing

  let body
  if (shipmentCount === 0) {
    body = <p className="empty">Nothing to track yet. Tracking appears once a shipment is created.</p>
  } else if (loading && !data) {
    body = (
      <div className="tcards" role="status" aria-label="Loading tracking">
        {Array.from({ length: Math.min(shipmentCount, 3) }, (_, i) => (
          <TrackingCardSkeleton key={i} />
        ))}
      </div>
    )
  } else if (error && !data) {
    body = (
      <div className="inline-error" role="alert">
        <p>Tracking could not be loaded: {error.message}</p>
        <button type="button" className="btn btn--small" onClick={() => load(false)}>
          Try again
        </button>
      </div>
    )
  } else if (data) {
    body = (
      <>
        {error ? (
          <p className="inline-error" role="alert">
            Refresh failed: {error.message} Showing the previous result.
          </p>
        ) : null}
        {data.shipments.length === 0 ? (
          <p className="empty">The carriers returned no tracking for this order.</p>
        ) : (
          <div className={refreshing ? 'tcards is-refreshing' : 'tcards'}>
            {data.shipments.map((t, i) => (
              <TrackingCard key={`${t.tracking_no}-${i}`} tracking={t} />
            ))}
          </div>
        )}
      </>
    )
  }

  return (
    <section className="panel" aria-labelledby="tracking-title" aria-busy={busy}>
      <header className="panel__head">
        <h2 id="tracking-title" className="section-title">
          Courier tracking
        </h2>
        <button type="button" className="btn" onClick={() => load(true)} disabled={busy || shipmentCount === 0}>
          {refreshing ? <Spinner label="Refreshing tracking" /> : null}
          {refreshing ? 'Checking carriers…' : 'Refresh tracking'}
        </button>
      </header>
      {body}
    </section>
  )
}
