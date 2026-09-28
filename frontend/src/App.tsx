import { createBrowserRouter, createMemoryRouter, RouterProvider } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ErrorPage } from './pages/ErrorPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { OrderDetailPage } from './pages/OrderDetailPage'
import { OrderListPage } from './pages/OrderListPage'
import { TrackingLookupPage } from './pages/TrackingLookupPage'

// VITE_PREVIEW builds (a standalone review page with mock data) cannot rely on the
// page URL, so they keep the route in memory instead.
const createRouter = import.meta.env.VITE_PREVIEW === 'true' ? createMemoryRouter : createBrowserRouter

const router = createRouter([
  {
    element: <Layout />,
    errorElement: <ErrorPage />,
    children: [
      { path: '/', element: <OrderListPage /> },
      { path: '/orders/:orderNo', element: <OrderDetailPage /> },
      { path: '/tracking', element: <TrackingLookupPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
