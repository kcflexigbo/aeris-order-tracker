import type { ReactNode } from 'react'
import type { Address, OrderDetail } from '../api/types'
import { formatDate } from '../lib/format'
import { StatusBadge } from './StatusBadge'

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="field">
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}

const missing = <span className="muted">Not provided</span>

export function ShippingAddress({ address }: { address: Address }) {
  const structured = address.line || address.suburb || address.state || address.postcode
  return (
    <section className="address" aria-labelledby="ship-to">
      <h2 id="ship-to" className="section-title">
        Ship to
      </h2>
      {structured ? (
        <address>
          {address.line ? <span>{address.line}</span> : null}
          <span>{[address.suburb, address.state, address.postcode].filter(Boolean).join(' ')}</span>
        </address>
      ) : (
        <address>
          <span>{address.raw || 'No address on file'}</span>
        </address>
      )}
      {structured && address.raw ? <p className="address__raw">As entered: {address.raw}</p> : null}
    </section>
  )
}

export function OrderHeader({ order }: { order: OrderDetail }) {
  return (
    <section className="order-head">
      <div className="order-head__main">
        <p className="order-head__company">{order.company ?? order.customer_name}</p>
        <div className="order-head__title">
          <h1 className="code-display">{order.order_no}</h1>
          <StatusBadge status={order.status} />
        </div>
        <dl className="fields">
          <Field label="Order date">{formatDate(order.order_date)}</Field>
          <Field label="Customer">{order.customer_name}</Field>
          <Field label="Company">{order.company ?? missing}</Field>
          <Field label="Phone">{order.phone ? <a href={`tel:${order.phone.replace(/\s+/g, '')}`}>{order.phone}</a> : missing}</Field>
          <Field label="Email">{order.email ? <a href={`mailto:${order.email}`}>{order.email}</a> : missing}</Field>
        </dl>
      </div>
      <ShippingAddress address={order.address} />
    </section>
  )
}
