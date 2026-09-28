import { useState } from 'react'
import type { LineStatus, OrderLine } from '../api/types'
import { carrierName, formatMoney, formatUnitPrice, plural } from '../lib/format'
import { ProductPlaceholder } from './ProductPlaceholder'

const STATUS_LABEL: Record<LineStatus, string> = {
  ok: 'OK',
  sku_not_found: 'SKU not found',
  invalid_quantity: 'Invalid quantity',
  missing_price: 'Missing price',
}

const DESCRIPTION_LIMIT = 90

function Description({ text }: { text: string }) {
  const [open, setOpen] = useState(false)
  if (text.length <= DESCRIPTION_LIMIT) return <p className="line__desc">{text}</p>
  const short = text.slice(0, DESCRIPTION_LIMIT).replace(/\s+\S*$/, '')
  return (
    <p className="line__desc">
      {open ? text : `${short}…`}{' '}
      <button type="button" className="link-btn" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        {open ? 'Show less' : 'Show more'}
      </button>
    </p>
  )
}

function Quantity({ line }: { line: OrderLine }) {
  if (line.quantity !== null) return <span className="num">{line.quantity}</span>
  const raw = line.quantity_raw.trim()
  return (
    <span className="qty-raw" title="Quantity as entered on the order">
      {raw ? `“${raw}”` : 'blank'}
    </span>
  )
}

function LineRow({ line }: { line: OrderLine }) {
  const flagged = line.status !== 'ok'
  return (
    <tr className={flagged ? 'line line--flagged' : 'line'}>
      <td className="line__product" data-label="Product">
        <div className="line__product-inner">
        <ProductPlaceholder label={line.image_label} dosageType={line.dosage_type} />
        <div className="line__info">
          <p className="line__name">
            {line.product_name ?? <span className="muted">Unknown product</span>}
          </p>
          <p className="line__meta">
            <span className="code">{line.sku}</span>
            {line.dosage_type ? <span>{line.dosage_type}</span> : null}
          </p>
          {line.description ? <Description text={line.description} /> : null}
          {flagged ? (
            <p className="line__flag" role="note">
              <strong>{STATUS_LABEL[line.status] ?? line.status}.</strong> {line.message ?? 'This line could not be priced.'}
            </p>
          ) : null}
        </div>
        </div>
      </td>
      <td className="line__num" data-label="Qty">
        <Quantity line={line} />
      </td>
      <td className="line__num" data-label="RRP (incl GST)">
        {formatMoney(line.rrp)}
      </td>
      <td className="line__num" data-label="Unit price (ex GST)">
        {formatUnitPrice(line.ex_gst_unit_price)}
      </td>
      <td className="line__num line__subtotal" data-label="Subtotal (ex GST)">
        {line.line_subtotal !== null && !flagged ? (
          formatMoney(line.line_subtotal)
        ) : (
          <span className="excluded">Excluded from totals</span>
        )}
      </td>
      <td className="line__ship" data-label="Shipment">
        {line.tracking_ref || line.tracking_no ? (
          <>
            <span className="line__ref">{line.tracking_ref ?? 'Shipment'}</span>
            <span className="line__carrier">
              {carrierName(line.carrier)}
              {line.tracking_no ? <span className="code"> {line.tracking_no}</span> : null}
            </span>
          </>
        ) : (
          <span className="muted">Not assigned</span>
        )}
      </td>
    </tr>
  )
}

export function SkuLines({ lines }: { lines: OrderLine[] }) {
  const flagged = lines.filter((l) => l.status !== 'ok').length
  return (
    <section className="panel" aria-labelledby="lines-title">
      <header className="panel__head">
        <h2 id="lines-title" className="section-title">
          Order lines
        </h2>
        <p className="panel__sub">
          {plural(lines.length, 'line')}
          {flagged > 0 ? <span className="chip chip--amber">{plural(flagged, 'line')} {flagged === 1 ? 'needs' : 'need'} attention</span> : null}
        </p>
      </header>
      {lines.length === 0 ? (
        <p className="empty">This order has no lines.</p>
      ) : (
        <div className="table-wrap">
          <table className="lines">
            <thead>
              <tr>
                <th scope="col">Product</th>
                <th scope="col" className="th-num">
                  Qty
                </th>
                <th scope="col" className="th-num">
                  RRP <small>incl GST</small>
                </th>
                <th scope="col" className="th-num">
                  Unit price <small>ex GST</small>
                </th>
                <th scope="col" className="th-num">
                  Subtotal <small>ex GST</small>
                </th>
                <th scope="col">Shipment</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line) => (
                <LineRow key={line.line_no} line={line} />
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="footnote">
        Ex-GST unit price = RRP ÷ 1.10, shown to 4 decimals; line subtotals are rounded to cents.
      </p>
    </section>
  )
}
