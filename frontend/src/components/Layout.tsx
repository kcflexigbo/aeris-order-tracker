import { NavLink, Outlet, Link } from 'react-router-dom'
import { USE_MOCKS } from '../api/client'
import { HealthIndicator } from './HealthIndicator'

export function Layout() {
  return (
    <div className="app">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="topbar">
        <div className="topbar__inner">
          <Link to="/" className="brand">
            <svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true" focusable="false">
              <rect x="10" y="4" width="12" height="5" rx="1.5" fill="currentColor" opacity="0.7" />
              <rect x="7" y="10" width="18" height="18" rx="3.5" fill="none" stroke="currentColor" strokeWidth="2" />
              <path d="M16 15v8M12 19h8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <span className="brand__name">Aeris Order Tracker</span>
          </Link>
          <nav className="nav" aria-label="Main">
            <NavLink to="/" end>
              Orders
            </NavLink>
            <NavLink to="/tracking">Track a parcel</NavLink>
          </nav>
          <HealthIndicator />
        </div>
      </header>
      {USE_MOCKS ? (
        <div className="mock-banner" role="note">
          Showing sample data (mock mode). Set VITE_USE_MOCKS=false to use the live API.
        </div>
      ) : null}
      <main id="main" className="main">
        <Outlet />
      </main>
      <footer className="footer">
        Aeris Health order and shipment tracking. Prices in Australian dollars; GST at 10%.
      </footer>
    </div>
  )
}
