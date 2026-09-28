from app.api import health, orders, tracking

routers = [health.router, orders.router, tracking.router]

__all__ = ["routers"]
