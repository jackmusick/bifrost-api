FROM node:20-slim

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm ci --production=false

# Copy source code
COPY . .

# # Build the application (creates dist/ folder with staticwebapp.config.json)
# RUN npm run build

RUN npm install

# Install only SWA CLI globally for serving
RUN npm install -g @azure/static-web-apps-cli

# Only expose SWA CLI port (production mode, no Vite dev server)
EXPOSE 4280

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Use entrypoint script to handle env var substitution
ENTRYPOINT ["/entrypoint.sh"]
