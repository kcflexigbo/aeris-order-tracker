import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '../api/client'

export interface AsyncState<T> {
  data: T | null
  error: ApiError | null
  loading: boolean
  /** Re-run the loader. Existing data stays visible while it reloads. */
  reload: () => void
  /** Replace data directly, e.g. with the response of a mutation. */
  setData: (value: T) => void
}

export function toApiError(err: unknown): ApiError {
  if (err instanceof ApiError) return err
  const message = err instanceof Error ? err.message : 'Something went wrong.'
  return new ApiError(message, -1)
}

/**
 * Runs `loader` whenever `deps` change. Responses from superseded runs are ignored,
 * so a slow earlier request can never overwrite a newer one.
 */
export function useAsync<T>(loader: () => Promise<T>, deps: readonly unknown[]): AsyncState<T> {
  const [data, setDataState] = useState<T | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [loading, setLoading] = useState(true)
  const [nonce, setNonce] = useState(0)
  const runId = useRef(0)
  const loaderRef = useRef(loader)
  loaderRef.current = loader

  useEffect(() => {
    const id = ++runId.current
    setLoading(true)
    setError(null)
    loaderRef
      .current()
      .then((value) => {
        if (id === runId.current) setDataState(value)
      })
      .catch((err: unknown) => {
        if (id === runId.current) setError(toApiError(err))
      })
      .finally(() => {
        if (id === runId.current) setLoading(false)
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce])

  const reload = useCallback(() => setNonce((n) => n + 1), [])
  const setData = useCallback((value: T) => {
    runId.current++ // cancel anything in flight
    setDataState(value)
    setError(null)
    setLoading(false)
  }, [])

  return { data, error, loading, reload, setData }
}
