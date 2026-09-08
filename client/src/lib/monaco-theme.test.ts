import { describe, it, expect, vi } from "vitest";
import { waitFor } from "@testing-library/react";
import type * as Monaco from "monaco-editor";
import { createMonacoTheme, watchMonacoTheme } from "./monaco-theme";
import { contrastRatio } from "./brand-palette";

describe("Bifrost editor theme", () => {
	for (const mode of ["light", "dark"] as const) {
		it(`keeps ${mode} code text readable and tenant identity separate from diagnostics`, () => {
			const theme = createMonacoTheme(mode, "#b50075");
			for (const color of Object.values(theme.colors))
				expect(color).toMatch(/^#[0-9a-f]{6}([0-9a-f]{2})?$/i);
			expect(theme.colors["editorCursor.foreground"]).toBe("#b50075");
			expect(theme.colors["editorError.foreground"]).not.toBe("#b50075");
			expect(
				contrastRatio(
					theme.colors["editor.foreground"],
					theme.colors["editor.background"],
				),
			).toBeGreaterThan(7);
			for (const [name, color] of Object.entries(theme.colors)) {
				if (name.startsWith("editorBracketHighlight.foreground")) {
					expect(
						contrastRatio(color, theme.colors["editor.background"]),
					).toBeGreaterThanOrEqual(4.5);
				}
			}
			for (const rule of theme.rules) {
				expect(
					contrastRatio(
						"#" + rule.foreground,
						theme.colors["editor.background"],
					),
				).toBeGreaterThanOrEqual(4.5);
			}
		});
	}
	it("rejects unresolved or invalid CSS colors", () => {
		expect(
			createMonacoTheme("dark", "var(--primary)").colors[
				"editorCursor.foreground"
			],
		).toBe("#2fd4d4");
	});
});

it("updates mounted editor colors after branding changes and disconnects on cleanup", async () => {
	const defineTheme = vi.fn();
	const setTheme = vi.fn();
	const monaco = {
		editor: { defineTheme, setTheme },
	} as unknown as typeof Monaco;
	const root = document.documentElement;
	const previous = root.style.getPropertyValue("--primary");
	root.style.setProperty("--primary", "#087f86");
	const cleanup = watchMonacoTheme(monaco, "light");
	try {
		root.style.setProperty("--primary", "#984565");
		await waitFor(() =>
			expect(
				defineTheme.mock.lastCall?.[1].colors[
					"editorCursor.foreground"
				],
			).toBe("#984565"),
		);
		expect(setTheme).toHaveBeenLastCalledWith("bifrost-light");
		cleanup();
		defineTheme.mockClear();
		root.style.setProperty("--primary", "#112233");
		await new Promise((resolve) => setTimeout(resolve, 0));
		expect(defineTheme).not.toHaveBeenCalled();
	} finally {
		cleanup();
		if (previous) root.style.setProperty("--primary", previous);
		else root.style.removeProperty("--primary");
	}
});
