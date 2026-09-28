import type { Quote, Shipment } from '../api/types'
import { carrierName, formatDateTime, formatMoney, formatParcel, plural } from '../lib/format'
import { Spinner } from './Feedback'

const QUOTE_PROBLEM: Record<Exclude<Quote['status'], 'ok'>, string> = {
  unavailable: 'Quote unavailable',
  not_implemented: 'No rating service for this carrier',
}

function QuoteBlock({ quote }: { quote: Quote | null }) {
  if (!quote) {
    return (
      <div className="quote quote--missing">
        <p className="quote__fee">{formatMoney('0.00')}</p>
        <p className="quote__reason">Not quoted yet. Use “Refresh quotes” to request a price.</p>
      </div>
    )
  }
  if (quote.status !== 'ok') {
    return (
      <div className={`quote quote--${quote.status}`}>
        <p className="quote__fee">
          {formatMoney('0.00')} <small>charged</small>
        </p>
        <p className="quote__reason">
          <strong>{QUOTE_PROBLEM[quote.status] ?? 'No quote'}.</strong> {quote.message ?? 'The carrier did not return a price.'}
        </p>
        {quote.source ? <p className="source-label">Source: {quote.source}</p> : null}
      </div>
    )
  }
  return (
    <div className="quote">
      <p className="quote__service">{quote.service_name ?? quote.service_code ?? 'Standard service'}</p>
      <p className="quote__fee">
        {formatMoney(quote.fee_incl_gst)} <small>incl GST</small>
      </p>
      <p className="quote__ex">{formatMoney(quote.fee_ex_gst)} ex GST</p>
      {quote.parcel ? (
        <p className="quote__parcel">
          Parcel {formatParcel(quote.parcel)}
          {quote.parcel.item_count ? `, ${plural(quote.parcel.item_count, 'item')}` : ''}
        </p>
      ) : null}
      <p className="source-label">
        {quote.source ?? 'Unknown source'}, quoted {formatDateTime(quote.quoted_at)}
      </p>
    </div>
  )
}

export function ShipmentsPanel({
  shipments,
  refreshing,
  refreshError,
  onRefresh,
}: {
  shipments: Shipment[]
  refreshing: boolean
  refreshError: string | null
  onRefresh: () => void
}) {
  return (
    <section className="panel" aria-labelledby="ship-title" aria-busy={refreshing}>
      <header className="panel__head">
        <h2 id="ship-title" className="section-title">
          Shipments and fees
        </h2>
        <button type="button" className="btn" onClick={onRefresh} disabled={refreshing || shipments.length === 0}>
          {refreshing ? <Spinner label="Refreshing quotes" /> : null}
          {refreshing ? 'Refreshing quotes…' : 'Refresh quotes'}
        </button>
      </header>
      {refreshError ? (
        <p className="inline-error" role="alert">
          Quotes were not refreshed: {refreshError}
        </p>
      ) : null}
      {shipments.length === 0 ? (
        <p className="empty">No shipments have been created for this order.</p>
      ) : (
        <ul className="shipments">
          {shipments.map((s) => (
            <li key={s.id} className="shipment">
              <div className="shipment__id">
                <p className="shipment__ref">{s.tracking_ref}</p>
                <p className="shipment__carrier">
                  {s.logistics_company || carrierName(s.carrier)}
                </p>
                <p className="code">{s.tracking_no}</p>
                <p className="muted small">{plural(s.line_count, 'line')}</p>
              </div>
              <QuoteBlock quote={s.quote} />
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
