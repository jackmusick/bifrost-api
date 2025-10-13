import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

// https://vite.dev/config/
export default defineConfig({
    plugins: [tailwindcss(), react()],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
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
        fs: {
            // Allow serving files from one level up to the project root
            allow: [".."],
        },
    },
});
