FROM node:20-slim

WORKDIR /app

# Expose ports
# 4280 is the default SWA CLI port
# 5173 is Vite dev server
EXPOSE 4280 5173

# Install dependencies on startup (picks up changes from mounted volume)
# Then start SWA CLI with Vite
CMD ["sh", "-c", "echo 'Installing dependencies...' && npm install && echo 'Starting SWA with API_URL=${API_URL}' && npm run dev:docker"]
