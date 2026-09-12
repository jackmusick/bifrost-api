import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type * as Monaco from "monaco-editor";
import { useBifrostMonacoTheme } from "./useBifrostMonacoTheme";
const mocks = vi.hoisted(() => ({
	theme: "dark",
	reduced: false,
	register: vi.fn(),
	watch: vi.fn(),
}));
vi.mock("@/contexts/ThemeContext", () => ({
	useTheme: () => ({ theme: mocks.theme }),
}));
vi.mock("./useMediaQuery", () => ({ useMediaQuery: () => mocks.reduced }));
vi.mock("@/lib/monaco-theme", () => ({
	registerMonacoTheme: mocks.register,
	watchMonacoTheme: mocks.watch,
}));

describe("secondary editor appearance lifecycle", () => {
	it("updates mounted editors, releases subscriptions, and supports a dialog reopening", () => {
		const cleanups: ReturnType<typeof vi.fn>[] = [];
		mocks.watch.mockImplementation(() => {
			const cleanup = vi.fn();
			cleanups.push(cleanup);
			return cleanup;
		});
		let dispose = () => {};
		const editor = {
			onDidDispose: (callback: () => void) => {
				dispose = callback;
			},
		} as unknown as Monaco.editor.IStandaloneCodeEditor;
		const monaco = {} as typeof Monaco;
		const view = renderHook(() => useBifrostMonacoTheme());
		act(() => {
			view.result.current.beforeMount(monaco);
			view.result.current.onMount(editor, monaco);
		});
		expect(mocks.register).toHaveBeenCalledWith(monaco, "dark");
		expect(mocks.watch).toHaveBeenLastCalledWith(monaco, "dark");
		mocks.theme = "light";
		mocks.reduced = true;
		view.rerender();
		expect(cleanups[0]).toHaveBeenCalled();
		expect(mocks.watch).toHaveBeenLastCalledWith(monaco, "light");
		expect(view.result.current.options.cursorBlinking).toBe("solid");
		act(() => dispose());
		expect(cleanups[1]).toHaveBeenCalled();
		act(() => view.result.current.onMount(editor, monaco));
		expect(mocks.watch).toHaveBeenCalledTimes(3);
		view.unmount();
		expect(cleanups[2]).toHaveBeenCalled();
	});
});
