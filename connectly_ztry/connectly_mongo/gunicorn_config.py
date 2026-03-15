# Production config for Gunicorn + Eventlet
# Render sets $PORT automatically — we read it here
import os

# Workers — SocketIO MUST use 1 worker with eventlet (no shared memory between workers)
workers        = 1
worker_class   = 'eventlet'
worker_connections = 1000

# Render provides PORT via environment variable
port           = os.environ.get('PORT', '5000')
bind           = f'0.0.0.0:{port}'

timeout        = 120
keepalive      = 5
loglevel       = 'warning'

# Preload app to share memory
preload_app    = False   # Must be False for SocketIO + eventlet
