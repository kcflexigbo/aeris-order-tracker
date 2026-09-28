// The only module in the app that talks to the network.
// When VITE_USE_MOCKS === "true" every call is served by ./mocks instead.

import type {
  Health,
  LookupCarrier,
  OrderDetail,
  OrderSummary,
  OrderTracking,
  Tracking,
} from './types'

export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true'

const API_BASE = '/api'

/** Error thrown for any failed API call. `status` is 0 when the server could not be reached. */
export class ApiError extends Error {
  readonly status: number
  readonly detail: string | null

  constructor(message: string, status: number, detail: string | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }

  get isNotFound(): boolean {
    return this.status === 404
  }

  get isNetwork(): boolean {
    return this.status === 0
  }
}

function detailFromBody(body: unknown): string | null {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    // FastAPI validation errors: [{loc, msg, type}]
    if (Array.isArray(detail)) {
      const msgs = detail
        .map((d) => (d && typeof d === 'object' && 'msg' in d ? String((d as { msg: unknown }).msg) : null))
        .filter((m): m is string => Boolean(m))
      if (msgs.length) return msgs.join('; ')
    }
  }
  return null
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { Accept: 'application/json', ...(init?.headers ?? {}) },
    })
  } catch {
    throw new ApiError('The order service could not be reached. Check your connection or that the backend is running.', 0)
  }

  const text = await res.text()
  let body: unknown = null
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = null
    }
  }

  if (!res.ok) {
    const detail = detailFromBody(body)
    const message =
      detail ??
      (res.status >= 500
        ? `The order service returned an error (HTTP ${res.status}).`
        : `Request failed (HTTP ${res.status}).`)
    throw new ApiError(message, res.status, detail)
  }
  if (body === null) {
    throw new ApiError('The order service returned an unreadable response.', res.status)
  }
  return body as T
}

const mocks = () => import('./mocks')

export async function getHealth(): Promise<Health> {
  if (USE_MOCKS) return (await mocks()).mockHealth()
  return request<Health>('/health')
}

export async function getOrders(): Promise<OrderSummary[]> {
  if (USE_MOCKS) return (await mocks()).mockOrders()
  return request<OrderSummary[]>('/orders')
}

export async function getOrder(orderNo: string): Promise<OrderDetail> {
  if (USE_MOCKS) return (await mocks()).mockOrder(orderNo)
  return request<OrderDetail>(`/orders/${encodeURIComponent(orderNo)}`)
}

export async function refreshShipping(orderNo: string): Promise<OrderDetail> {
  if (USE_MOCKS) return (await mocks()).mockRefreshShipping(orderNo)
  return request<OrderDetail>(`/orders/${encodeURIComponent(orderNo)}/shipping/refresh`, { method: 'POST' })
}

export async function getOrderTracking(orderNo: string, refresh = false): Promise<OrderTracking> {
  if (USE_MOCKS) return (await mocks()).mockOrderTracking(orderNo, refresh)
  return request<OrderTracking>(
    `/orders/${encodeURIComponent(orderNo)}/tracking?refresh=${refresh ? 'true' : 'false'}`,
  )
}

export async function lookupTracking(carrier: LookupCarrier, ids: string[]): Promise<Tracking[]> {
  if (USE_MOCKS) return (await mocks()).mockLookupTracking(carrier, ids)
  const params = new URLSearchParams({ carrier, ids: ids.join(',') })
  return request<Tracking[]>(`/tracking?${params.toString()}`)
}
