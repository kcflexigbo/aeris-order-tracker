# Gunicorn manages the processes; each worker runs the async app on Uvicorn.
import os

bind = "0.0.0.0:8000"
worker_class = "uvicorn_worker.UvicornWorker"
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
# Above the 15 s courier HTTP timeout, so a slow carrier fails cleanly first
timeout = 60
graceful_timeout = 30
keepalive = 5
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
