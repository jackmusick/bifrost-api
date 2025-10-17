FROM node:20-slim

WORKDIR /app

# Install dependencies first (better caching)
COPY package*.json ./
RUN npm ci

# Copy the rest of the application
COPY . .

# Expose ports
# 4280 is the default SWA CLI port
# 5173 is Vite dev server
EXPOSE 4280 5173

# Start SWA CLI with Vite
# The API URL will be provided via environment variable
CMD ["sh", "-c", "echo 'Starting SWA with API_URL=${API_URL}' && npm run dev:docker"]
