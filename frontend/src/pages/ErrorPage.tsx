import { useRouteError } from 'react-router-dom'

/** Shown instead of React Router's developer error screen if a page throws while rendering. */
export function ErrorPage() {
  const error = useRouteError()
  console.error(error)
  return (
    <main className="main" style={{ padding: 24 }}>
      <div className="state state--error" role="alert">
        <h2 className="state__title">Something went wrong on this page</h2>
        <p className="state__body">
          The page could not be displayed. Reload to try again, or go back to the order list.
        </p>
        <div className="state__actions">
          <button type="button" className="btn btn--primary" onClick={() => window.location.reload()}>
            Reload
          </button>
          <a className="btn" href="/">
            All orders
          </a>
        </div>
      </div>
    </main>
  )
}
