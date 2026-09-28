import { useEffect, useState } from 'react'
import { getHealth } from '../api/client'
import type { Health } from '../api/types'

type View = { kind: 'checking' } | { kind: 'ok' | 'degraded'; health: Health } | { kind: 'down' }

const POLL_MS = 30_000

const LABEL: Record<View['kind'], string> = {
  checking: 'Checking services',
  ok: 'All services up',
  degraded: 'Degraded',
  down: 'API unreachable',
}

export function HealthIndicator() {
  const [view, setView] = useState<View>({ kind: 'checking' })

  useEffect(() => {
    let alive = true
    const check = () =>
      getHealth()
        .then((health) => alive && setView({ kind: health.status === 'ok' ? 'ok' : 'degraded', health }))
        .catch(() => alive && setView({ kind: 'down' }))
    void check()
    const timer = window.setInterval(check, POLL_MS)
    return () => {
      alive = false
      window.clearInterval(timer)
    }
  }, [])

  const rows: [string, boolean][] =
    view.kind === 'ok' || view.kind === 'degraded'
      ? [
          ['Database', view.health.database],
          ['Cache (Redis)', view.health.redis],
          ['Australia Post / StarTrack API', view.health.auspost_configured],
          ['TNT rating API', view.health.tnt_rtt_configured],
        ]
      : []

  return (
    <details className={`health health--${view.kind}`}>
      <summary aria-label={`Service status: ${LABEL[view.kind]}`}>
        <span className="health__dot" aria-hidden="true" />
        <span className="health__label">{LABEL[view.kind]}</span>
      </summary>
      <div className="health__panel">
        {view.kind === 'down' ? (
          <p>The backend did not answer the health check. Pages will show an error until it is back.</p>
        ) : view.kind === 'checking' ? (
          <p>Checking the backend…</p>
        ) : (
          <ul>
            {rows.map(([name, up]) => (
              <li key={name} className={up ? 'is-up' : 'is-down'}>
                <span aria-hidden="true">{up ? '✓' : '✕'}</span> {name}
                <span className="sr-only">{up ? ' available' : ' not available'}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </details>
  )
}
