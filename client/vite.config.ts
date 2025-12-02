import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";
import { copyFileSync } from "fs";

// https://vite.dev/config/
export default defineConfig({
	plugins: [
		tailwindcss(),
		react(),
		{
			name: "copy-staticwebapp-config",
			closeBundle() {
				copyFileSync(
					"staticwebapp.config.json",
					"dist/staticwebapp.config.json",
				);
			},
		},
	],
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "./src"),
		},
	},
	build: {
		rollupOptions: {
			output: {
				manualChunks: {
					// React core - always needed
					"react-vendor": ["react", "react-dom", "react-router-dom"],

					// Monaco Editor - large dependency, split separately
					monaco: ["monaco-editor", "@monaco-editor/react"],

					// Babel standalone - only for JSX template rendering (used in FormRenderer)
					babel: ["@babel/standalone"],

					// UI framework - Radix UI primitives
					"ui-primitives": [
						"@radix-ui/react-dialog",
						"@radix-ui/react-dropdown-menu",
						"@radix-ui/react-label",
						"@radix-ui/react-slot",
						"@radix-ui/react-tooltip",
						"@radix-ui/react-select",
						"@radix-ui/react-separator",
						"@radix-ui/react-tabs",
						"@radix-ui/react-alert-dialog",
						"@radix-ui/react-popover",
						"@radix-ui/react-checkbox",
						"@radix-ui/react-context-menu",
						"@radix-ui/react-radio-group",
						"@radix-ui/react-switch",
						"@radix-ui/react-toggle",
						"@radix-ui/react-toggle-group",
					],

					// Animation libraries
					animations: [
						"framer-motion",
						"@atlaskit/pragmatic-drag-and-drop",
						"@atlaskit/pragmatic-drag-and-drop-auto-scroll",
						"@atlaskit/pragmatic-drag-and-drop-hitbox",
					],

					// Data fetching and state
					data: ["@tanstack/react-query", "zustand"],

					// Syntax highlighting
					"syntax-highlighter": ["react-syntax-highlighter"],

					// Forms
					forms: ["react-hook-form", "@hookform/resolvers", "zod"],

					// UI Utils
					"ui-utils": [
						"lucide-react",
						"sonner",
						"clsx",
						"tailwind-merge",
						"class-variance-authority",
					],

					// Content rendering
					"content-rendering": [
						"dompurify",
						"react-markdown",
						"date-fns",
						"react-day-picker",
					],
				},
			},
		},
		chunkSizeWarningLimit: 3000, // Increase limit - babel-standalone is inherently large (2.9MB) but lazy-loaded only when needed for JSX templates
	},
	optimizeDeps: {
		include: [
			"react",
			"react-dom",
			"react-router-dom",
			"@tanstack/react-query",
			"lucide-react",
			"sonner",
			// Pre-bundle common Radix UI packages to reduce request count
			"@radix-ui/react-dialog",
			"@radix-ui/react-dropdown-menu",
			"@radix-ui/react-label",
			"@radix-ui/react-slot",
			"@radix-ui/react-tooltip",
			"@radix-ui/react-select",
			"@radix-ui/react-separator",
			"@radix-ui/react-tabs",
			"@radix-ui/react-alert-dialog",
			"@radix-ui/react-popover",
		],
	},
	server: {
		host: "0.0.0.0",
		port: 3000,
		strictPort: true, // Fail if port is already in use
		hmr: {
			// When running in Docker, HMR connects directly to Vite
			// When running behind SWA proxy, set clientPort: 4280
		},
		watch: {
			usePolling: true,
			interval: 1000,
		},
		proxy: {
			// Use API_URL env var for Docker (api:8000) or default to localhost:8000 for local dev
			// Rewrite /api/auth/* to /auth/* since backend auth routes don't have /api prefix
			"/api/auth": {
				target: process.env.API_URL || "http://localhost:8000",
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/auth/, "/auth"),
			},
			"/api": {
				target: process.env.API_URL || "http://localhost:8000",
				changeOrigin: true,
			},
			"/auth": {
				target: process.env.API_URL || "http://localhost:8000",
				changeOrigin: true,
			},
			"/ws": {
				target: process.env.WS_URL || "ws://localhost:8000",
				ws: true,
			},
		},
	},
});
