// Types mirroring the backend JSON contract exactly.
// Money and decimal quantities are strings: the backend does all arithmetic.

export type HealthStatus = 'ok' | 'degraded'

export interface Health {
  status: HealthStatus
  database: boolean
  redis: boolean
  auspost_configured: boolean
  tnt_rtt_configured: boolean
}

export type Carrier = 'STARTRACK' | 'TNT' | 'UNKNOWN'

export interface OrderSummary {
  order_no: string
  order_date: string // YYYY-MM-DD
  status: string
  company: string | null
  customer_name: string
  destination: string | null
  line_count: number
  flagged_lines: number
  shipment_count: number
}

export interface Address {
  raw: string
  line: string | null
  suburb: string | null
  state: string | null
  postcode: string | null
}

export type LineStatus = 'ok' | 'sku_not_found' | 'invalid_quantity' | 'missing_price'

export interface OrderLine {
  line_no: number
  image_label: string
  sku: string
  product_name: string | null
  description: string | null
  dosage_type: string | null
  quantity: number | null
  quantity_raw: string
  rrp: string | null // GST inclusive
  ex_gst_unit_price: string | null // 4dp
  line_subtotal: string | null // ex GST; null when excluded
  status: LineStatus
  message: string | null
  tracking_ref: string | null
  tracking_no: string | null
  carrier: Carrier | null
}

export interface Parcel {
  length_cm: number
  width_cm: number
  height_cm: number
  weight_kg: string
  item_count: number
}

export type QuoteStatus = 'ok' | 'unavailable' | 'not_implemented'

export interface Quote {
  status: QuoteStatus
  service_code: string | null
  service_name: string | null
  fee_ex_gst: string
  fee_incl_gst: string
  message: string | null
  source: string | null
  parcel: Parcel | null
  quoted_at: string // ISO datetime
}

export interface Shipment {
  id: number
  tracking_ref: string
  tracking_no: string
  carrier: Carrier
  logistics_company: string
  line_count: number
  quote: Quote | null
}

export interface Totals {
  currency: 'AUD'
  subtotal: string
  gst: string
  shipment_fee: string
  total: string
  excluded_lines: number
}

export interface OrderDetail {
  order_no: string
  order_date: string
  status: string
  company: string | null
  customer_name: string
  phone: string | null
  email: string | null
  address: Address
  lines: OrderLine[]
  shipments: Shipment[]
  totals: Totals
  warnings: string[]
}

export type TrackingState = 'ok' | 'not_found' | 'unavailable' | 'not_implemented'

export interface TrackingEvent {
  description: string
  location: string | null
  occurred_at: string | null
}

export interface Tracking {
  tracking_ref: string | null
  tracking_no: string
  carrier: Carrier
  state: TrackingState
  status: string | null
  last_update: string | null
  last_location: string | null
  events: TrackingEvent[] // newest first
  message: string | null
  error_code: string | null
  source: string | null
  fetched_at: string
  cached: boolean
}

export interface OrderTracking {
  order_no: string
  shipments: Tracking[]
}

export type LookupCarrier = 'STARTRACK' | 'TNT'
