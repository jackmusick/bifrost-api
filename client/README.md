# Bifrost Client

React-based frontend for the Bifrost automation platform.

## Overview

This is the Static Web App (SWA) frontend for Bifrost. It connects to the [Bifrost API](https://github.com/jackmusick/bifrost-api) backend.

## Technologies

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **UI**: shadcn/ui components with Tailwind CSS
- **Hosting**: Azure Static Web Apps

## Prerequisites

- Node.js 20+
- Access to a deployed Bifrost API or local API instance

## Local Development

### Option 1: Standalone Development

```bash
# Install dependencies
npm install

# Start dev server
npm run dev
```

The app will run at `http://localhost:5173` and connect to your API endpoint (configure in `.env.local`).

### Option 2: Full Stack with Docker Compose

For local development with the complete stack (API + Client), see the main [Bifrost API repository](https://github.com/jackmusick/bifrost-api).

## Environment Configuration

Copy `.env.example` to `.env.local` and configure:

```bash
# API endpoint (production or local)
VITE_API_URL=https://your-api.azurewebsites.net

# Or for local development
VITE_API_URL=http://localhost:7071
```

## Build

```bash
npm run build
```

Output will be in `dist/` directory.

## Deployment

This app is designed to be deployed as an Azure Static Web App with "bring your own function" backend.

### Azure Portal Deployment

1. Create an Azure Static Web App
2. Link to this GitHub repository
3. Configure build:
    - App location: `/`
    - API location: (leave empty - using external API)
    - Output location: `dist`
4. Add environment variables in SWA configuration

### GitHub Actions (Manual)

Azure deployment center will create a workflow file automatically when you link your GitHub repo. See [Azure Static Web Apps documentation](https://learn.microsoft.com/en-us/azure/static-web-apps/getting-started).

## Project Structure

```
src/
├── components/       # Reusable UI components
├── pages/           # Page components (Dashboard, Forms, Workflows, etc.)
├── hooks/           # Custom React hooks for API calls
├── services/        # API client wrappers
├── lib/             # Utilities and types
└── contexts/        # React contexts
```

## Configuration

- `staticwebapp.config.json` - SWA routing and authentication
- `tailwind.config.js` - Tailwind CSS configuration
- `components.json` - shadcn/ui configuration
- `tsconfig.json` - TypeScript configuration
- `vite.config.ts` - Vite build configuration

## Related Repositories

- [Bifrost API](https://github.com/jackmusick/bifrost-api) - Azure Functions backend

## License

MIT
