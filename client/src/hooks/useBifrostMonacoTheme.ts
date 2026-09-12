import { useCallback, useEffect, useRef } from "react";
import type * as Monaco from "monaco-editor";
import { useTheme } from "@/contexts/ThemeContext";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { registerMonacoTheme, watchMonacoTheme } from "@/lib/monaco-theme";

/** One theme subscription per editor, including editors mounted inside dialogs. */
export function useBifrostMonacoTheme() {
	const { theme } = useTheme();
	const reducedMotion = useMediaQuery("(prefers-reduced-motion: reduce)");
	const monacoRef = useRef<typeof Monaco | null>(null);
	const cleanupRef = useRef<(() => void) | null>(null);
	useEffect(() => {
		if (monacoRef.current) {
			cleanupRef.current?.();
			cleanupRef.current = watchMonacoTheme(monacoRef.current, theme);
		}
		return () => cleanupRef.current?.();
	}, [theme]);
	const beforeMount = useCallback(
		(monaco: typeof Monaco) => registerMonacoTheme(monaco, theme),
		[theme],
	);
	const onMount = useCallback(
		(
			editor:
				| Monaco.editor.IStandaloneCodeEditor
				| Monaco.editor.IStandaloneDiffEditor,
			monaco: typeof Monaco,
		) => {
			monacoRef.current = monaco;
			cleanupRef.current?.();
			cleanupRef.current = watchMonacoTheme(monaco, theme);
			editor.onDidDispose(() => {
				cleanupRef.current?.();
				cleanupRef.current = null;
				monacoRef.current = null;
			});
		},
		[theme],
	);
	return {
		theme: `bifrost-${theme}`,
		beforeMount,
		onMount,
		options: {
			fontFamily: '"JetBrains Mono", "SFMono-Regular", Consolas, monospace',
			fontSize: 13,
			lineHeight: 21,
			cursorBlinking: reducedMotion
				? ("solid" as const)
				: ("blink" as const),
			smoothScrolling: !reducedMotion,
		},
	};
}
