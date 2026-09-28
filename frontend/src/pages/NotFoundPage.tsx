import { Link } from 'react-router-dom'

export function NotFoundState({ orderNo }: { orderNo?: string }) {
  return (
    <div className="state state--notfound">
      <p className="state__code" aria-hidden="true">
        404
      </p>
      <h1 className="state__title">{orderNo ? 'Order not found' : 'Page not found'}</h1>
      <p className="state__body">
        {orderNo ? (
          <>
            There is no order with the number <span className="code">{orderNo}</span>. Check the number, or pick the order
            from the list.
          </>
        ) : (
          'This address does not match any page in the order tracker.'
        )}
      </p>
      <div className="state__actions">
        <Link className="btn btn--primary" to="/">
          Go to orders
        </Link>
      </div>
    </div>
  )
}

export function NotFoundPage() {
  return (
    <div className="page">
      <NotFoundState />
    </div>
  )
}
