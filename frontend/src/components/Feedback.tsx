import type { ReactNode } from 'react'
import type { ApiError } from '../api/client'

export function Spinner({ label }: { label?: string }) {
  return (
    <span className="spinner" role="status">
      <span className="spinner__ring" aria-hidden="true" />
      {label ? <span className="sr-only">{label}</span> : null}
    </span>
  )
}

export function Skeleton({ width, height = '1em', className = '' }: { width?: string; height?: string; className?: string }) {
  return <span className={`skeleton ${className}`} style={{ width, height }} aria-hidden="true" />
}

export function ErrorState({
  title = 'Could not load this page',
  error,
  onRetry,
  children,
}: {
  title?: string
  error: ApiError | null
  onRetry?: () => void
  children?: ReactNode
}) {
  const unreachable = error?.isNetwork || (error ? error.status >= 500 : false)
  return (
    <div className="state state--error" role="alert">
      <h2 className="state__title">{title}</h2>
      <p className="state__body">
        {unreachable
          ? 'The order service is not responding right now. Your data is safe; try again in a moment.'
          : error?.message ?? 'Something went wrong.'}
      </p>
      {unreachable && error ? <p className="state__detail">{error.message}</p> : null}
      <div className="state__actions">
        {onRetry ? (
          <button type="button" className="btn btn--primary" onClick={onRetry}>
            Try again
          </button>
        ) : null}
        {children}
      </div>
    </div>
  )
}

export function Notice({ tone, children }: { tone: 'amber' | 'red' | 'grey' | 'green'; children: ReactNode }) {
  return <div className={`notice notice--${tone}`}>{children}</div>
}
