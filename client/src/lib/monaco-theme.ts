import type * as Monaco from "monaco-editor";

export function createMonacoTheme(
	mode: "light" | "dark",
	primary?: string,
): Monaco.editor.IStandaloneThemeData {
	const dark = mode === "dark";
	const accent =
		primary && /^#[0-9a-f]{6}$/i.test(primary)
			? primary
			: dark
				? "#2fd4d4"
				: "#087f86";
	const canvas = dark ? "#0a0c0f" : "#ffffff";
	const raised = dark ? "#11151a" : "#eef2f3";
	const ink = dark ? "#dce5eb" : "#101419";
	const border = dark ? "#252c34" : "#d7dfe3";
	return {
		base: dark ? "vs-dark" : "vs",
		inherit: true,
		rules: [
			{ token: "comment", foreground: dark ? "80929f" : "627480" },
			{ token: "string", foreground: dark ? "82d9a0" : "28713d" },
			{ token: "keyword", foreground: dark ? "b4a2ff" : "6846b2" },
			{ token: "number", foreground: dark ? "ffc477" : "925820" },
			{ token: "type", foreground: dark ? "68cde2" : "087a91" },
		],
		colors: {
			"editor.background": canvas,
			"editor.foreground": ink,
			"editorGutter.background": canvas,
			// Keep diagnostic hints from washing out otherwise readable code.
			"editorUnnecessaryCode.opacity": "#000000ff",
			"editorBracketHighlight.foreground1": dark ? "#b4a2ff" : "#6846b2",
			"editorBracketHighlight.foreground2": dark ? "#82d9a0" : "#28713d",
			"editorBracketHighlight.foreground3": dark ? "#ffc477" : "#925820",
			"editorBracketHighlight.foreground4": dark ? "#68cde2" : "#087a91",
			"editorBracketHighlight.foreground5": dark ? "#ffabb8" : "#a03653",
			"editorBracketHighlight.foreground6": dark ? "#dce5eb" : "#101419",
			"editor.lineHighlightBackground": raised,
			"editorLineNumber.foreground": dark ? "#647480" : "#75858f",
			"editorLineNumber.activeForeground": ink,
			"editorCursor.foreground": accent,
			"editor.selectionBackground": accent + "33",
			"editor.inactiveSelectionBackground": accent + "1f",
			"editor.selectionHighlightBackground": accent + "18",
			"editorWidget.background": raised,
			"editorWidget.border": border,
			"editorSuggestWidget.background": raised,
			"editorSuggestWidget.border": border,
			"editorSuggestWidget.foreground": ink,
			"editorSuggestWidget.selectedBackground": accent + "22",
			"editorHoverWidget.background": raised,
			"editorHoverWidget.border": border,
			focusBorder: accent,
			"editorError.foreground": dark ? "#ff727a" : "#b4232d",
			"editorWarning.foreground": dark ? "#ffc154" : "#8a5a00",
			"editorInfo.foreground": dark ? "#69b9ff" : "#1769aa",
		},
	};
}

/** Monaco accepts resolved colors, so register the current tenant's semantic accent. */
export function registerMonacoTheme(
	monaco: typeof Monaco,
	mode: "light" | "dark",
) {
	const primary = getComputedStyle(document.documentElement)
		.getPropertyValue("--primary")
		.trim();
	monaco.editor.defineTheme(
		`bifrost-${mode}`,
		createMonacoTheme(mode, primary),
	);
}

/** Keep mounted editors in sync with theme switches and branding preview updates. */
export function watchMonacoTheme(
	monaco: typeof Monaco,
	mode: "light" | "dark",
) {
	const update = () => {
		registerMonacoTheme(monaco, mode);
		monaco.editor.setTheme(`bifrost-${mode}`);
	};
	update();
	const observer = new MutationObserver(update);
	observer.observe(document.documentElement, {
		attributes: true,
		attributeFilter: ["class", "style"],
	});
	const branding = document.getElementById("bifrost-branding-theme");
	if (branding)
		observer.observe(branding, {
			childList: true,
			characterData: true,
			subtree: true,
		});
	return () => observer.disconnect();
}
