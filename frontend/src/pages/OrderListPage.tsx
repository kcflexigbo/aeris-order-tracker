import { useNavigate, Link } from 'react-router-dom'
import { getOrders } from '../api/client'
import { ErrorState, Skeleton } from '../components/Feedback'
import { StatusBadge } from '../components/StatusBadge'
import { formatDate, plural } from '../lib/format'
import { useAsync } from '../lib/useAsync'

function ListSkeleton() {
  return (
    <div className="table-wrap" role="status" aria-label="Loading orders">
      <table className="orders">
        <tbody>
          {Array.from({ length: 4 }, (_, i) => (
            <tr key={i}>
              <td>
                <Skeleton width="11rem" />
              </td>
              <td>
                <Skeleton width="6rem" />
              </td>
              <td>
                <Skeleton width="12rem" />
              </td>
              <td>
                <Skeleton width="9rem" />
              </td>
              <td>
                <Skeleton width="5rem" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function OrderListPage() {
  const { data, error, loading, reload } = useAsync(getOrders, [])
  const navigate = useNavigate()

  return (
    <div className="page">
      <header className="page-head">
        <h1>Orders</h1>
        <p className="page-head__sub">
          Wholesale orders with their SKU pricing, shipment fees and courier tracking.
        </p>
      </header>

      {loading && !data ? (
        <ListSkeleton />
      ) : error && !data ? (
        <ErrorState title="Orders could not be loaded" error={error} onRetry={reload} />
      ) : data && data.length === 0 ? (
        <div className="state">
          <h2 className="state__title">No orders yet</h2>
          <p className="state__body">Orders imported into the system will appear here.</p>
        </div>
      ) : data ? (
        <div className="table-wrap">
          <table className="orders">
            <thead>
              <tr>
                <th scope="col">Order</th>
                <th scope="col">Date</th>
                <th scope="col">Customer</th>
                <th scope="col">Destination</th>
                <th scope="col">Lines</th>
              </tr>
            </thead>
            <tbody>
              {data.map((o) => (
                <tr
                  key={o.order_no}
                  className="orders__row"
                  onClick={(e) => {
                    // Let real links / modified clicks behave normally.
                    if ((e.target as HTMLElement).closest('a') || e.metaKey || e.ctrlKey) return
                    navigate(`/orders/${encodeURIComponent(o.order_no)}`)
                  }}
                >
                  <td data-label="Order">
                    <div className="orders__id">
                    <Link className="orders__no code-strong" to={`/orders/${encodeURIComponent(o.order_no)}`}>
                      {o.order_no}
                    </Link>
                    <StatusBadge status={o.status} />
                    </div>
                  </td>
                  <td data-label="Date">{formatDate(o.order_date)}</td>
                  <td data-label="Customer">
                    <span className="orders__company">{o.company ?? o.customer_name}</span>
                    {o.company ? <span className="orders__person">{o.customer_name}</span> : null}
                  </td>
                  <td data-label="Destination">{o.destination ?? <span className="muted">Unknown</span>}</td>
                  <td data-label="Lines">
                    <span className="orders__counts">
                      {plural(o.line_count, 'line')}, {plural(o.shipment_count, 'shipment')}
                    </span>
                    {o.flagged_lines > 0 ? (
                      <span className="chip chip--amber">{plural(o.flagged_lines, 'flagged line')}</span>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  )
}
