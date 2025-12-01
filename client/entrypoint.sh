#!/bin/sh
set -e

# Default values
# API_URL=${API_URL:-http://api:80}

# Start SWA CLI serving the built static files
# The staticwebapp.config.json in dist/ references ENTRA_CLIENT_ID and ENTRA_CLIENT_SECRET
# SWA CLI will read these from the environment at runtime
# exec swa start dist --api-location "$API_URL" --port 4280
# exec swa start \
#     --app-devserver-url http://localhost:5173 \
#     --api-devserver-url "$API_URL" \
#     --run "npm run dev" \
#     --host localhost \
#     --port 4280

exec swa start

