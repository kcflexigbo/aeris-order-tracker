#!/bin/sh
# Runs once per container start, before any worker exists:
# apply migrations, load the input data, then hand over to Gunicorn.
set -e

alembic upgrade head
python -m app.seed
exec gunicorn -c gunicorn.conf.py app.main:app
