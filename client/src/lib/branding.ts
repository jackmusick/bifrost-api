/**
 * Branding utilities for dynamic theming
 * Applies organization-specific branding (logos and colors) via CSS variables
 */

import type { components } from "@/lib/v1";

export type BrandingSettings = components["schemas"]["BrandingSettings"];

/**
 * Convert hex color to OKLCH format
 * Uses proper XYZ color space transformation for accurate perceptual color conversion
 */
function hexToOklch(hexColor: string): string {
	// Remove # if present
	const hex = hexColor.replace(/^#/, "");

	// Parse hex values to sRGB (0-1 range)
	const r = parseInt(hex.slice(0, 2), 16) / 255;
	const g = parseInt(hex.slice(2, 4), 16) / 255;
	const b = parseInt(hex.slice(4, 6), 16) / 255;

	// Convert sRGB to linear RGB
	const toLinear = (c: number) =>
		c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
	const lr = toLinear(r);
	const lg = toLinear(g);
	const lb = toLinear(b);

	// Convert linear RGB to XYZ (D65 illuminant)
	const x = 0.4124564 * lr + 0.3575761 * lg + 0.1804375 * lb;
	const y = 0.2126729 * lr + 0.7151522 * lg + 0.072175 * lb;
	const z = 0.0193339 * lr + 0.119192 * lg + 0.9503041 * lb;

	// Convert XYZ to OKLab
	const l_ = Math.cbrt(
		0.8189330101 * x + 0.3618667424 * y - 0.1288597137 * z,
	);
	const m_ = Math.cbrt(
		0.0329845436 * x + 0.9293118715 * y + 0.0361456387 * z,
	);
	const s_ = Math.cbrt(0.0482003018 * x + 0.2643662691 * y + 0.633851707 * z);

	const L = 0.2104542553 * l_ + 0.793617785 * m_ - 0.0040720468 * s_;
	const a = 1.9779984951 * l_ - 2.428592205 * m_ + 0.4505937099 * s_;
	const b_ = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.808675766 * s_;

	// Convert OKLab to OKLCH
	const C = Math.sqrt(a * a + b_ * b_);
	let H = Math.atan2(b_, a) * (180 / Math.PI);
	if (H < 0) H += 360;

	return `oklch(${L.toFixed(3)} ${C.toFixed(3)} ${H.toFixed(1)})`;
}

/**
 * Get contrasting foreground color in OKLCH format for accessibility
 */
function getContrastingForegroundOKLCH(hex: string): string {
	// Remove # if present
	hex = hex.replace(/^#/, "");

	// Parse hex values
	const r = parseInt(hex.slice(0, 2), 16);
	const g = parseInt(hex.slice(2, 4), 16);
	const b = parseInt(hex.slice(4, 6), 16);

	// Calculate relative luminance
	const luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;

	// Return white or black based on luminance
	// White: oklch(0.985 0 0) - very light
	// Black: oklch(0.205 0 0) - very dark
	return luminance > 0.5 ? "0.205 0 0" : "0.985 0 0";
}

/**
 * Apply branding theme to the document
 * Updates CSS custom properties for instant visual updates
 */
export function applyBrandingTheme(branding: BrandingSettings | null) {
	const root = document.documentElement;

	// Default branding (fallback) - teal color from theme
	const defaultColor = "#0066CC";

	const primaryColor = branding?.primary_color || defaultColor;
	const oklchColor = hexToOklch(primaryColor);

	// Debug: log the conversion

	// Update the theme's primary color variables
	// Set both the source variables AND the Tailwind theme variables
	root.style.setProperty("--primary", oklchColor);
	root.style.setProperty("--sidebar-primary", oklchColor);
	root.style.setProperty("--color-primary", oklchColor);
	root.style.setProperty("--color-sidebar-primary", oklchColor);

	// Calculate and set contrasting foreground color for text readability
	const foregroundOklch = getContrastingForegroundOKLCH(primaryColor);
	root.style.setProperty("--primary-foreground", `oklch(${foregroundOklch})`);
	root.style.setProperty(
		"--sidebar-primary-foreground",
		`oklch(${foregroundOklch})`,
	);

	// For dark mode, we need to adjust the lightness for better contrast
	// Extract L, C, H from oklchColor
	const match = oklchColor.match(
		/oklch\(([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\)/,
	);
	if (match && match[1] && match[2] && match[3]) {
		const l = match[1];
		const c = match[2];
		const h = match[3];
		const lightness = parseFloat(l);
		// Increase lightness for dark mode
		const darkModeLightness = Math.min(1, lightness + 0.2);
		const darkModeColor = `oklch(${darkModeLightness.toFixed(
			3,
		)} ${c} ${h})`;

		// Calculate contrasting foreground for dark mode
		const darkModeForeground = getContrastingForegroundOKLCH(primaryColor);

		// Set dark mode override - need to override both source and theme variables
		// Also override compiled Tailwind classes to use runtime CSS variables
		const darkModeStyles = root.querySelector('style[data-theme="dark"]');
		const styleContent = `
      .dark {
        --primary: ${darkModeColor};
        --sidebar-primary: ${darkModeColor};
        --color-primary: ${darkModeColor};
        --color-sidebar-primary: ${darkModeColor};
        --primary-foreground: oklch(${darkModeForeground});
        --sidebar-primary-foreground: oklch(${darkModeForeground});
      }
    `;

		if (darkModeStyles) {
			darkModeStyles.textContent = styleContent;
		} else {
			const style = document.createElement("style");
			style.setAttribute("data-theme", "dark");
			style.textContent = styleContent;
			document.head.appendChild(style);
		}
	}

	// Force Tailwind components to use runtime CSS variables
	// This overrides the build-time compiled values
	let brandingOverride = document.querySelector(
		"style[data-branding-override]",
	);
	if (!brandingOverride) {
		brandingOverride = document.createElement("style");
		brandingOverride.setAttribute("data-branding-override", "true");
		document.head.appendChild(brandingOverride);
	}

	brandingOverride.textContent = `
    /* Override Tailwind compiled classes with runtime CSS variables */
    /* Only match exact classes, not partial matches to avoid affecting inputs with bg-primary/opacity */
    .bg-primary:not([class*="/"]) {
      background-color: ${oklchColor} !important;
    }
    .text-primary:not([class*="/"]) {
      color: ${oklchColor} !important;
    }
    .border-primary:not([class*="/"]) {
      border-color: ${oklchColor} !important;
    }

    /* Dark mode overrides */
    .dark .bg-primary:not([class*="/"]) {
      background-color: var(--primary) !important;
    }
    .dark .text-primary:not([class*="/"]) {
      color: var(--primary) !important;
    }
    .dark .border-primary:not([class*="/"]) {
      border-color: var(--primary) !important;
    }
  `;

	// Apply logo URLs as CSS variables (for use in background-image)
	if (branding?.square_logo_url) {
		root.style.setProperty(
			"--logo-square-url",
			`url('${branding.square_logo_url}')`,
		);
	} else {
		root.style.removeProperty("--logo-square-url");
	}

	if (branding?.rectangle_logo_url) {
		root.style.setProperty(
			"--logo-rectangle-url",
			`url('${branding.rectangle_logo_url}')`,
		);
	} else {
		root.style.removeProperty("--logo-rectangle-url");
	}
}

/**
 * Fetch branding settings from API
 * Public endpoint - always returns GLOBAL branding
 */
export async function fetchBranding(): Promise<BrandingSettings | null> {
	try {
		const response = await fetch("/api/branding");

		if (!response.ok) {
			console.warn("Failed to fetch branding, using defaults");
			return null;
		}

		const branding = await response.json();
		return branding;
	} catch {
		return null;
	}
}

/**
 * Initialize branding on app load
 * Fetches GLOBAL branding and applies theme
 */
export async function initializeBranding() {
	const branding = await fetchBranding();
	applyBrandingTheme(branding);
	return branding;
}
