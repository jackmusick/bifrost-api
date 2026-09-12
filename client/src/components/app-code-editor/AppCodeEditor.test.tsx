import { useEffect } from "react";
import { act, render } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { AppCodeEditor } from "./AppCodeEditor";

const mount = vi.hoisted(() => ({
	save: undefined as (() => void) | undefined,
}));
vi.mock("@/contexts/ThemeContext", () => ({
	useTheme: () => ({ theme: "light" }),
}));
vi.mock("@/hooks/useMediaQuery", () => ({ useMediaQuery: () => false }));
vi.mock("@/lib/monaco-setup", () => ({ initializeMonaco: vi.fn() }));
vi.mock("@/lib/monaco-theme", () => ({
	registerMonacoTheme: vi.fn(),
	watchMonacoTheme: () => vi.fn(),
}));
vi.mock("@monaco-editor/react", () => ({
	default: function MockMonaco({
		onMount,
	}: {
		onMount: (editor: unknown, monaco: unknown) => void;
	}) {
		useEffect(() => {
			onMount(
				{
					addCommand: (_key: number, callback: () => void) => {
						mount.save = callback;
					},
					onDidDispose: vi.fn(),
					focus: vi.fn(),
					getModel: () => null,
				},
				{ KeyMod: { CtrlCmd: 1 }, KeyCode: { KeyS: 2 } },
			);
			// Monaco registers commands once for the lifetime of an editor instance.
			// eslint-disable-next-line react-hooks/exhaustive-deps
		}, []);
		return null;
	},
}));

it("keyboard save follows the latest buffer callback without remounting Monaco", () => {
	const initialSave = vi.fn();
	const editedSave = vi.fn();
	const props = { value: "initial", onChange: vi.fn(), onSave: initialSave };
	const view = render(<AppCodeEditor {...props} />);
	const command = mount.save;
	view.rerender(
		<AppCodeEditor {...props} value="edited" onSave={editedSave} />,
	);
	expect(mount.save).toBe(command);
	act(() => mount.save?.());
	expect(initialSave).not.toHaveBeenCalled();
	expect(editedSave).toHaveBeenCalledOnce();
});
