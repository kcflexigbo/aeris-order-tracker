// Fixture data used when VITE_USE_MOCKS=true. Values mirror the assessment data set.
// Every call simulates network latency so loading states are visible.

import { ApiError } from './client'
import type {
  Carrier,
  Health,
  LookupCarrier,
  OrderDetail,
  OrderLine,
  OrderSummary,
  OrderTracking,
  Parcel,
  Quote,
  Shipment,
  Tracking,
  TrackingEvent,
} from './types'

const LATENCY_MS = 400
const QUOTE_LATENCY_MS = 1800

function delay(ms = LATENCY_MS): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

const QUOTED_AT = '2026-09-28T09:12:04+10:00'
const AUSPOST_RATES = 'Australia Post testbed (test rates)'
const TNT_RATES = 'TNT RTT (UAT test rates)'
const TNT_TRACKING_SOURCE = 'TNT consignment history (public weblink)'

// ---------------------------------------------------------------- products

interface Product {
  name: string
  description: string
  dosage_type: string
  rrp: string
  ex: string
}

const PRODUCTS: Record<string, Product> = {
  TBAMET10: {
    name: 'Amethyst THC 25% 10G',
    description: 'Dried flower, THC-dominant sativa-leaning cultivar. Supplied in a 10 g child-resistant jar.',
    dosage_type: 'Dried flower',
    rrp: '99.00',
    ex: '90.0000',
  },
  TBAMET28: {
    name: 'Amethyst THC 25% 28G',
    description: 'Dried flower, THC-dominant sativa-leaning cultivar. Supplied in a 28 g child-resistant jar.',
    dosage_type: 'Dried flower',
    rrp: '199.00',
    ex: '180.9091',
  },
  TBOPAL28: {
    name: 'Opal THC 23% 28G',
    description: 'Dried flower, balanced hybrid cultivar with a mild terpene profile. 28 g jar.',
    dosage_type: 'Dried flower',
    rrp: '199.00',
    ex: '180.9091',
  },
  HARNIG: {
    name: 'Harbour LR Night Cartridge',
    description:
      'Pre-filled 1 mL vaporiser cartridge formulated for evening use. Compatible with standard 510-thread batteries only; battery not included. Store upright below 25 °C away from direct sunlight, and keep out of reach of children.',
    dosage_type: 'Vaporiser cartridge',
    rrp: '149.00',
    ex: '135.4545',
  },
  LELCBD100: {
    name: 'CBD 100 - Full Spectrum Certified Organic',
    description:
      'Full-spectrum CBD oil, 100 mg/mL, in MCT carrier oil from certified organic hemp. 25 mL amber glass bottle with graduated dropper. Shake well before use and refrigerate after opening.',
    dosage_type: 'Oral liquid',
    rrp: '140.00',
    ex: '127.2727',
  },
  AURPUR10: {
    name: 'Purple Raine THC18% 15g',
    description: 'Dried flower, indica-leaning cultivar. 15 g nitrogen-flushed pouch.',
    dosage_type: 'Dried flower',
    rrp: '99.00',
    ex: '90.0000',
  },
  HALGEO15: {
    name: 'The Geoffrey CBG 12% 15g',
    description: 'Dried flower, CBG-dominant with low THC. 15 g jar.',
    dosage_type: 'Dried flower',
    rrp: '110.00',
    ex: '100.0000',
  },
  MCMW10: {
    name: 'Maali Wind THC 25% 10g',
    description: 'Dried flower, small-batch hand-trimmed cultivar. 10 g jar.',
    dosage_type: 'Dried flower',
    rrp: '129.00',
    ex: '117.2727',
  },
  MCBO30: {
    name: 'BOB 30 (Alien OG) THC 30% 10g',
    description: 'Dried flower, high-potency THC cultivar. 10 g jar.',
    dosage_type: 'Dried flower',
    rrp: '99.00',
    ex: '90.0000',
  },
}

interface Track {
  ref: string
  no: string
  carrier: Carrier
}

const T1: Track = { ref: 'Track 1', no: '2FWZ50008569', carrier: 'STARTRACK' }
const T2: Track = { ref: 'Track 2', no: '2FWZ50008645', carrier: 'STARTRACK' }
const T3: Track = { ref: 'Track 3', no: '305506914', carrier: 'TNT' }
const T4: Track = { ref: 'Track 4', no: 'RBXZ50016112', carrier: 'STARTRACK' }
const T5: Track = { ref: 'Track 5', no: '2FWZ50020500', carrier: 'STARTRACK' }
const T6: Track = { ref: 'Track 6', no: 'BAD#CONNOTE', carrier: 'TNT' }

function okLine(line_no: number, sku: string, quantity: number, subtotal: string, t: Track): OrderLine {
  const p = PRODUCTS[sku]
  return {
    line_no,
    image_label: `Product ${line_no}`,
    sku,
    product_name: p.name,
    description: p.description,
    dosage_type: p.dosage_type,
    quantity,
    quantity_raw: String(quantity),
    rrp: p.rrp,
    ex_gst_unit_price: p.ex,
    line_subtotal: subtotal,
    status: 'ok',
    message: null,
    tracking_ref: t.ref,
    tracking_no: t.no,
    carrier: t.carrier,
  }
}

function invalidQtyLine(line_no: number, sku: string, raw: string, t: Track): OrderLine {
  return {
    ...okLine(line_no, sku, 0, '0.00', t),
    quantity: null,
    quantity_raw: raw,
    line_subtotal: null,
    status: 'invalid_quantity',
    message: `quantity must be a positive whole number, got '${raw}'`,
  }
}

function cube(cm: number, kg: string, items: number): Parcel {
  return { length_cm: cm, width_cm: cm, height_cm: cm, weight_kg: kg, item_count: items }
}

function shipment(id: number, t: Track, line_count: number, fees: [string, string], parcel: Parcel): Shipment {
  const isTnt = t.carrier === 'TNT'
  const quote: Quote = {
    status: 'ok',
    service_code: isTnt ? '76' : 'EXP',
    service_name: isTnt ? 'Road Express' : 'StarTrack Express',
    fee_ex_gst: fees[0],
    fee_incl_gst: fees[1],
    message: null,
    source: isTnt ? TNT_RATES : AUSPOST_RATES,
    parcel,
    quoted_at: QUOTED_AT,
  }
  return {
    id,
    tracking_ref: t.ref,
    tracking_no: t.no,
    carrier: t.carrier,
    logistics_company: isTnt ? 'TNT Australia' : 'StarTrack',
    line_count,
    quote,
  }
}

// ---------------------------------------------------------------- orders

const ORDERS: OrderDetail[] = [
  {
    order_no: 'PO-20251130-00072',
    order_date: '2025-11-30',
    status: 'Completed',
    company: 'V22 Dispensary',
    customer_name: 'Jason Hu',
    phone: '0481 735 488',
    email: 'Jason@aerishealth.au',
    address: {
      raw: '125 Toorak Road, South Yarra VIC 3141',
      line: '125 Toorak Road',
      suburb: 'SOUTH YARRA',
      state: 'VIC',
      postcode: '3141',
    },
    lines: [
      okLine(1, 'TBAMET10', 3, '270.00', T1),
      okLine(2, 'TBAMET28', 1, '180.91', T1),
      okLine(3, 'TBOPAL28', 1, '180.91', T1),
      okLine(4, 'HARNIG', 4, '541.82', T1),
      okLine(5, 'LELCBD100', 6, '763.64', T1),
    ],
    shipments: [shipment(1, T1, 5, ['14.79', '16.27'], cube(19, '1.29', 15))],
    totals: { currency: 'AUD', subtotal: '1937.28', gst: '193.73', shipment_fee: '16.27', total: '2147.28', excluded_lines: 0 },
    warnings: [],
  },
  {
    order_no: 'PO-20251203-00046',
    order_date: '2025-12-03',
    status: 'In Transit',
    company: 'Cann Life Dispensary',
    customer_name: 'Bella Dari',
    phone: '0411 547 288',
    email: 'Bella@aerishealth.au',
    address: {
      raw: '381 Smith Street, Fitzroy VIC 3065',
      line: '381 Smith Street',
      suburb: 'FITZROY',
      state: 'VIC',
      postcode: '3065',
    },
    lines: [
      okLine(1, 'AURPUR10', 10, '900.00', T2),
      okLine(2, 'HALGEO15', 1, '100.00', T3),
      okLine(3, 'MCMW10', 2, '234.55', T3),
      okLine(4, 'MCBO30', 3, '270.00', T3),
    ],
    shipments: [
      shipment(2, T2, 1, ['14.79', '16.27'], cube(18, '0.98', 10)),
      shipment(3, T3, 3, ['18.18', '20.00'], cube(16, '0.67', 6)),
    ],
    totals: { currency: 'AUD', subtotal: '1504.55', gst: '150.46', shipment_fee: '36.27', total: '1691.28', excluded_lines: 0 },
    warnings: [],
  },
  {
    order_no: 'PO-TEST-0001',
    order_date: '2026-09-15',
    status: 'Processing',
    company: 'Test Harbour Pharmacy (fictitious)',
    customer_name: 'Test Customer A',
    phone: null,
    email: null,
    address: {
      raw: '1 Test Street, Brisbane City QLD 4000',
      line: '1 Test Street',
      suburb: 'BRISBANE CITY',
      state: 'QLD',
      postcode: '4000',
    },
    lines: [
      okLine(1, 'MCBO30', 2, '180.00', T4),
      {
        line_no: 2,
        image_label: 'Product 2',
        sku: 'NOTASKU99',
        product_name: null,
        description: null,
        dosage_type: null,
        quantity: 1,
        quantity_raw: '1',
        rrp: null,
        ex_gst_unit_price: null,
        line_subtotal: null,
        status: 'sku_not_found',
        message: 'SKU NOTASKU99 was not found in the product data',
        tracking_ref: T4.ref,
        tracking_no: T4.no,
        carrier: T4.carrier,
      },
      invalidQtyLine(3, 'TBAMET10', '0', T4),
    ],
    shipments: [shipment(4, T4, 3, ['9.95', '10.95'], cube(11, '0.42', 2))],
    totals: { currency: 'AUD', subtotal: '180.00', gst: '18.00', shipment_fee: '10.95', total: '208.95', excluded_lines: 2 },
    warnings: ['2 lines are excluded from the totals'],
  },
  {
    order_no: 'PO-TEST-0002',
    order_date: '2026-09-20',
    status: 'In Transit',
    company: 'Test Westside Clinic (fictitious)',
    customer_name: 'Test Customer B',
    phone: null,
    email: null,
    address: {
      raw: '2 Example Avenue, Perth WA 6000',
      line: '2 Example Avenue',
      suburb: 'PERTH',
      state: 'WA',
      postcode: '6000',
    },
    lines: [
      okLine(1, 'HALGEO15', 5, '500.00', T5),
      invalidQtyLine(2, 'LELCBD100', 'two', T5),
      okLine(3, 'HARNIG', 2, '270.91', T6),
    ],
    shipments: [
      shipment(5, T5, 2, ['9.95', '10.95'], cube(15, '0.64', 5)),
      shipment(6, T6, 1, ['39.58', '43.54'], cube(9, '0.35', 2)),
    ],
    totals: { currency: 'AUD', subtotal: '770.91', gst: '77.09', shipment_fee: '54.49', total: '902.49', excluded_lines: 1 },
    warnings: ['1 line is excluded from the totals'],
  },
]

function summarise(o: OrderDetail): OrderSummary {
  const a = o.address
  const destination = a.suburb && a.state && a.postcode ? `${a.suburb} ${a.state} ${a.postcode}` : null
  return {
    order_no: o.order_no,
    order_date: o.order_date,
    status: o.status,
    company: o.company,
    customer_name: o.customer_name,
    destination,
    line_count: o.lines.length,
    flagged_lines: o.lines.filter((l) => l.status !== 'ok').length,
    shipment_count: o.shipments.length,
  }
}

function findOrder(orderNo: string): OrderDetail {
  const order = ORDERS.find((o) => o.order_no.toLowerCase() === orderNo.toLowerCase())
  if (!order) {
    const detail = `Order ${orderNo} not found`
    throw new ApiError(detail, 404, detail)
  }
  return order
}

// ---------------------------------------------------------------- tracking

const STARTRACK_EVENTS: TrackingEvent[] = [
  { description: 'Delivered', location: 'LAKE CARGELLIGO NSW', occurred_at: '2025-02-13T11:49:59+11:00' },
  { description: 'Onboard for delivery', location: 'WEST WYALONG NSW', occurred_at: '2025-02-13T09:38:37+11:00' },
  { description: 'Item processed at sorting facility', location: 'EAST WAGGA WAGGA NSW', occurred_at: '2025-02-12T06:01:28+11:00' },
  { description: 'Item processed at sorting facility', location: 'TULLAMARINE VIC', occurred_at: '2025-02-11T22:14:41+11:00' },
  { description: 'Shipping information received by Australia Post', location: null, occurred_at: '2025-02-11T00:11:15+11:00' },
]

const TNT_EVENTS: TrackingEvent[] = [
  { description: "We've delivered your shipment", location: 'Melbourne - Airport', occurred_at: '2025-12-04T13:00:41' },
  { description: "Your shipment's with a driver", location: 'Melbourne - Airport', occurred_at: '2025-12-04T09:16:49' },
  { description: "We're processing your shipment", location: 'Melbourne - Airport', occurred_at: '2025-12-04T07:33:03' },
  { description: "We're processing your shipment", location: 'Melbourne - Airport', occurred_at: '2025-12-04T06:31:03' },
  { description: "We're processing your shipment", location: 'Sydney - Enfield', occurred_at: '2025-12-03T19:04:10' },
  { description: "We've collected your shipment", location: 'Sydney - Enfield', occurred_at: '2025-12-03T15:27:46' },
  { description: 'Your shipment data is lodged', location: 'Sydney - Enfield', occurred_at: '2025-12-03T10:21:14' },
]

function base(no: string, carrier: Carrier, ref: string | null, fresh: boolean): Tracking {
  const fetched = fresh ? new Date() : new Date(Date.now() - 7 * 60 * 1000)
  return {
    tracking_ref: ref,
    tracking_no: no,
    carrier,
    state: 'ok',
    status: null,
    last_update: null,
    last_location: null,
    events: [],
    message: null,
    error_code: null,
    source: null,
    fetched_at: fetched.toISOString(),
    cached: !fresh,
  }
}

/**
 * Demo ids for the lookup page:
 *  - FAIL123  -> "unavailable" (carrier API auth failure)
 *  - LEGACY1  -> "not_implemented"
 *  - any TNT id other than 305506914 -> "not_found"
 */
function trackOne(no: string, carrier: Carrier, ref: string | null, fresh: boolean): Tracking {
  const t = base(no, carrier, ref, fresh)
  const id = no.trim().toUpperCase()

  if (id === 'FAIL123') {
    return {
      ...t,
      state: 'unavailable',
      message: 'Australia Post returned HTTP 401: The request failed authentication',
      error_code: 'API_001',
      source: 'Australia Post tracking API',
      cached: false,
    }
  }
  if (id === 'LEGACY1' || carrier === 'UNKNOWN') {
    return { ...t, state: 'not_implemented', message: 'Tracking is not available for this carrier yet', cached: false }
  }

  if (carrier === 'TNT') {
    if (!/^[A-Z0-9]+$/.test(id)) {
      return {
        ...t,
        state: 'not_found',
        message: 'Not a valid TNT consignment number (letters and digits only)',
        error_code: 'INVALID_CONNOTE',
        source: TNT_TRACKING_SOURCE,
      }
    }
    if (id !== '305506914') {
      return {
        ...t,
        state: 'not_found',
        message: `TNT has no consignment history for ${id}`,
        error_code: 'NOT_FOUND',
        source: TNT_TRACKING_SOURCE,
      }
    }
    return {
      ...t,
      status: "We've delivered your shipment",
      last_update: TNT_EVENTS[0].occurred_at,
      last_location: TNT_EVENTS[0].location,
      events: TNT_EVENTS,
      source: TNT_TRACKING_SOURCE,
    }
  }

  // STARTRACK: the Australia Post testbed returns the same simulated history for any id.
  return {
    ...t,
    status: 'Delivered in Full',
    last_update: STARTRACK_EVENTS[0].occurred_at,
    last_location: STARTRACK_EVENTS[0].location,
    events: STARTRACK_EVENTS,
    source: 'Australia Post testbed (simulated data)',
  }
}

// ---------------------------------------------------------------- mock API (mirrors client.ts)

export async function mockHealth(): Promise<Health> {
  await delay()
  return { status: 'ok', database: true, redis: true, auspost_configured: true, tnt_rtt_configured: true }
}

export async function mockOrders(): Promise<OrderSummary[]> {
  await delay()
  return ORDERS.map(summarise)
}

export async function mockOrder(orderNo: string): Promise<OrderDetail> {
  await delay()
  return structuredClone(findOrder(orderNo))
}

export async function mockRefreshShipping(orderNo: string): Promise<OrderDetail> {
  await delay(QUOTE_LATENCY_MS)
  const order = findOrder(orderNo)
  const now = new Date().toISOString()
  for (const s of order.shipments) {
    if (s.quote) s.quote.quoted_at = now
  }
  return structuredClone(order)
}

export async function mockOrderTracking(orderNo: string, refresh: boolean): Promise<OrderTracking> {
  await delay(refresh ? 1200 : 900)
  const order = findOrder(orderNo)
  return {
    order_no: order.order_no,
    shipments: order.shipments.map((s) => trackOne(s.tracking_no, s.carrier, s.tracking_ref, refresh)),
  }
}

export async function mockLookupTracking(carrier: LookupCarrier, ids: string[]): Promise<Tracking[]> {
  await delay(700)
  if (ids.length === 0) throw new ApiError('Enter at least one tracking number.', 422)
  if (ids.length > 10) throw new ApiError('Look up at most 10 tracking numbers at a time.', 422)
  return ids.map((id) => trackOne(id, carrier, null, true))
}
