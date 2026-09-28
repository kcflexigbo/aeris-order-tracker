import type { Totals } from '../api/types'
import { formatMoney, plural } from '../lib/format'

export function TotalsSummary({ totals }: { totals: Totals }) {
  return (
    <section className="totals" aria-labelledby="totals-title">
      <h2 id="totals-title" className="section-title">
        Order total
      </h2>
      <dl className="totals__rows">
        <div>
          <dt>Subtotal (ex GST)</dt>
          <dd>{formatMoney(totals.subtotal)}</dd>
        </div>
        <div>
          <dt>GST (10%)</dt>
          <dd>{formatMoney(totals.gst)}</dd>
        </div>
        <div>
          <dt>Shipment fee</dt>
          <dd>{formatMoney(totals.shipment_fee)}</dd>
        </div>
        <div className="totals__grand">
          <dt>
            Total <small>{totals.currency ?? 'AUD'}, incl GST</small>
          </dt>
          <dd>{formatMoney(totals.total)}</dd>
        </div>
      </dl>
      {totals.excluded_lines > 0 ? (
        <p className="totals__note">
          {plural(totals.excluded_lines, 'line')} excluded from these totals. See the flagged lines above.
        </p>
      ) : null}
    </section>
  )
}
