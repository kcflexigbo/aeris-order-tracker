import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getOrder, refreshShipping } from '../api/client'
import { ErrorState, Notice, Skeleton } from '../components/Feedback'
import { OrderHeader } from '../components/OrderHeader'
import { ShipmentsPanel } from '../components/ShipmentsPanel'
import { SkuLines } from '../components/SkuLines'
import { TotalsSummary } from '../components/TotalsSummary'
import { TrackingPanel } from '../components/TrackingPanel'
import { toApiError, useAsync } from '../lib/useAsync'
import { NotFoundState } from './NotFoundPage'

function DetailSkeleton() {
  return (
    <div className="detail-skeleton" role="status" aria-label="Loading order">
      <section className="order-head">
        <div className="order-head__main">
          <Skeleton width="10rem" />
          <Skeleton width="16rem" height="2rem" />
          <div className="fields">
            {Array.from({ length: 5 }, (_, i) => (
              <Skeleton key={i} width="8rem" height="2.4em" />
            ))}
          </div>
        </div>
        <div className="address">
          <Skeleton width="6rem" />
          <Skeleton width="11rem" />
          <Skeleton width="9rem" />
        </div>
      </section>
      <section className="panel">
        {Array.from({ length: 4 }, (_, i) => (
          <div className="skeleton-row" key={i}>
            <Skeleton width="56px" height="56px" />
            <Skeleton width="40%" />
            <Skeleton width="15%" />
          </div>
        ))}
      </section>
    </div>
  )
}

function OrderDetailView({ orderNo }: { orderNo: string }) {
  const { data: order, error, loading, reload, setData } = useAsync(() => getOrder(orderNo), [orderNo])
  const [refreshing, setRefreshing] = useState(false)
  const [refreshError, setRefreshError] = useState<string | null>(null)

  const onRefreshQuotes = () => {
    setRefreshing(true)
    setRefreshError(null)
    refreshShipping(orderNo)
      .then(setData)
      .catch((err: unknown) => setRefreshError(toApiError(err).message))
      .finally(() => setRefreshing(false))
  }

  if (loading && !order) return <DetailSkeleton />
  if (error && !order) {
    if (error.isNotFound) return <NotFoundState orderNo={orderNo} />
    return (
      <ErrorState title={`Order ${orderNo} could not be loaded`} error={error} onRetry={reload}>
        <Link className="btn" to="/">
          Back to orders
        </Link>
      </ErrorState>
    )
  }
  if (!order) return null

  return (
    <div className="detail">
      <OrderHeader order={order} />

      {order.warnings.length > 0 ? (
        <Notice tone="amber">
          <ul className="warnings">
            {order.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </Notice>
      ) : null}

      <SkuLines lines={order.lines} />

      <div className="detail__money">
        <ShipmentsPanel
          shipments={order.shipments}
          refreshing={refreshing}
          refreshError={refreshError}
          onRefresh={onRefreshQuotes}
        />
        <TotalsSummary totals={order.totals} />
      </div>

      <TrackingPanel orderNo={order.order_no} shipmentCount={order.shipments.length} />
    </div>
  )
}

export function OrderDetailPage() {
  const { orderNo = '' } = useParams()
  return (
    <div className="page">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/">All orders</Link>
      </nav>
      {/* key: remount per order so state from a previous order never flashes */}
      <OrderDetailView key={orderNo} orderNo={orderNo} />
    </div>
  )
}
