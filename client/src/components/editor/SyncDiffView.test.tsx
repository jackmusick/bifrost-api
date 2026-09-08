import { act, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { SyncDiffView } from "./SyncDiffView";
vi.mock("@monaco-editor/react", () => ({
	DiffEditor: ({
		original,
		modified,
		options,
	}: {
		original: string;
		modified: string;
		options: { renderSideBySide: boolean };
	}) => (
		<div aria-label="Comparison model">
			<span>{original}</span>
			<span>{modified}</span>
			<span>{options.renderSideBySide ? "Two panes" : "One pane"}</span>
		</div>
	),
}));
vi.mock("@/hooks/useBifrostMonacoTheme", () => ({
	useBifrostMonacoTheme: () => ({
		theme: "test",
		options: {},
		beforeMount: vi.fn(),
		onMount: vi.fn(),
	}),
}));
afterEach(() => vi.unstubAllGlobals());
it("uses actual container width for split views and labels remote original before local modified", () => {
	let resize!: (entries: { contentRect: { width: number } }[]) => void;
	vi.stubGlobal(
		"ResizeObserver",
		class {
			constructor(callback: typeof resize) {
				resize = callback;
			}
			observe() {}
			disconnect() {}
		},
	);
	render(
		<SyncDiffView
			preview={{
				path: "workflow.py",
				displayName: "Workflow",
				entityType: "workflow",
				isConflict: true,
				remoteContent: "remote original",
				localContent: "local modified",
			}}
		/>,
	);
	expect(
		screen.getByText("Remote → Local · Unified comparison"),
	).toBeVisible();
	expect(screen.getByText("One pane")).toBeVisible();
	act(() => resize([{ contentRect: { width: 900 } }]));
	expect(screen.getByText("Two panes")).toBeVisible();
	expect(screen.getByText("Remote", { exact: true })).toBeVisible();
	expect(screen.getByText("Local", { exact: true })).toBeVisible();
	expect(screen.getByLabelText("Comparison model")).toHaveTextContent(
		"remote originallocal modified",
	);
	act(() => resize([{ contentRect: { width: 320 } }]));
	expect(screen.getByText("One pane")).toBeVisible();
});

it("retains file identity and exposes retry instead of rendering an empty diff on failure", async () => {
 const onRetry = vi.fn();
 vi.stubGlobal("ResizeObserver", class {observe(){} disconnect(){} });
 render(<SyncDiffView preview={{path:"workflows/failed.py",displayName:"Failed comparison",entityType:"workflow",isConflict:false,remoteContent:null,localContent:null,error:"Repository unavailable",onRetry}} />);
 expect(screen.getByRole("heading",{name:"Failed comparison"})).toBeVisible();
 expect(screen.getByRole("alert")).toHaveTextContent("Repository unavailable");
 expect(screen.queryByLabelText("Comparison model")).not.toBeInTheDocument();
 screen.getByRole("button",{name:"Retry comparison"}).click();
 expect(onRetry).toHaveBeenCalledTimes(1);
});
