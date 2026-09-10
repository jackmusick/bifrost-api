/// <reference types="vitest" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
	plugins: [react()],
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "./src"),
		},
	},
	test: {
		environment: "happy-dom",
		globals: true,
		setupFiles: ["./src/test/setup.ts"],
		include: ["src/**/*.test.{ts,tsx}"],
		// Exclude Playwright e2e specs so they don't accidentally run here
		exclude: ["e2e/**", "node_modules/**", "dist/**"],
		// happy-dom suites are CPU-heavy, and this repository commonly runs
		// several worktree test stacks at once. Keep an absolute cap so larger
		// hosts do not turn that shared load into interaction-test timeouts.
		maxWorkers: 2,
		css: false,
	},
});
