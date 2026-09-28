import { useId, useState } from 'react'
import type { Tracking, TrackingEvent, TrackingState } from '../api/types'
import { carrierName, formatDateTime, formatRelative } from '../lib/format'
import { Skeleton } from './Feedback'

const VISIBLE_EVENTS = 4

const STATE_TITLE: Record<TrackingState, string> = {
  ok: 'Tracking',
  not_found: 'Tracking number not found',
  unavailable: 'Tracking service unavailable',
  not_implemented: 'Tracking not supported',
}

const STATE_FALLBACK: Record<TrackingState, string> = {
  ok: '',
  not_found: 'The carrier has no record of this tracking number.',
  unavailable: 'The carrier did not respond. Try refreshing in a few minutes.',
  not_implemented: 'Live tracking is not available for this carrier.',
}

function Timeline({ events }: { events: TrackingEvent[] }) {
  const [expanded, setExpanded] = useState(false)
  const listId = useId()
  if (events.length === 0) return <p className="muted small">The carrier has not reported any scan events yet.</p>
  const shown = expanded ? events : events.slice(0, VISIBLE_EVENTS)
  const hidden = events.length - shown.length
  return (
    <div className="timeline-wrap">
      <ol className="timeline" id={listId} aria-label="Scan events, newest first">
        {shown.map((e, i) => (
          <li key={`${e.occurred_at ?? 'x'}-${i}`} className={i === 0 ? 'timeline__item is-latest' : 'timeline__item'}>
            <p className="timeline__desc">{e.description || 'Scan event'}</p>
            <p className="timeline__meta">
              {e.occurred_at ? <time dateTime={e.occurred_at}>{formatDateTime(e.occurred_at)}</time> : <span>Time not reported</span>}
              {e.location ? <span>{e.location}</span> : null}
            </p>
          </li>
        ))}
      </ol>
      {events.length > VISIBLE_EVENTS ? (
        <button
          type="button"
          className="link-btn"
          aria-expanded={expanded}
          aria-controls={listId}
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? 'Show fewer events' : `Show ${hidden} earlier ${hidden === 1 ? 'event' : 'events'}`}
        </button>
      ) : null}
    </div>
  )
}

export function TrackingCard({ tracking }: { tracking: Tracking }) {
  const state: TrackingState = STATE_TITLE[tracking.state] ? tracking.state : 'unavailable'
  const simulated = (tracking.source ?? '').toLowerCase().includes('simulated')
  const events = tracking.events ?? []

  return (
    <article className={`tcard tcard--${state}`}>
      <header className="tcard__head">
        <div>
          <p className="tcard__carrier">
            {carrierName(tracking.carrier)}
            {tracking.tracking_ref ? <span className="tcard__ref">{tracking.tracking_ref}</span> : null}
          </p>
          <p className="code tcard__no">{tracking.tracking_no || 'No tracking number'}</p>
        </div>
        {simulated ? <span className="badge badge--sim">Simulated testbed data</span> : null}
      </header>

      {state === 'ok' ? (
        <div className="tcard__body">
          <p className="tcard__status">{tracking.status ?? 'No status reported'}</p>
          <p className="tcard__last">
            {tracking.last_update ? `Last update ${formatDateTime(tracking.last_update)}` : 'No update time reported'}
            {tracking.last_location ? `, ${tracking.last_location}` : ''}
          </p>
          <Timeline events={events} />
        </div>
      ) : (
        <div className="tcard__body tcard__problem">
          <p className="tcard__status">{STATE_TITLE[state]}</p>
          <p>{tracking.message ?? STATE_FALLBACK[state]}</p>
          {tracking.error_code ? (
            <p className="small">
              Error code <span className="code">{tracking.error_code}</span>
            </p>
          ) : null}
          {events.length > 0 ? <Timeline events={events} /> : null}
        </div>
      )}

      <footer className="tcard__foot">
        <span>{tracking.source ? `Source: ${tracking.source}` : 'Source not reported'}</span>
        <span title={formatDateTime(tracking.fetched_at)}>
          {tracking.cached ? 'Cached result, fetched ' : 'Fetched '}
          {formatRelative(tracking.fetched_at)}
        </span>
      </footer>
    </article>
  )
}

export function TrackingCardSkeleton() {
  return (
    <div className="tcard tcard--loading" aria-hidden="true">
      <Skeleton width="40%" />
      <Skeleton width="60%" height="1.4em" />
      <Skeleton width="80%" />
      <Skeleton width="70%" />
      <Skeleton width="75%" />
    </div>
  )
}
