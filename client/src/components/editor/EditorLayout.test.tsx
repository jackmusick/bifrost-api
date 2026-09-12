import { act } from "@testing-library/react";
/**
 * Component tests for EditorLayout responsive shell behavior.
 */

// @vitest-environment happy-dom

import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { useState } from "react";
import { renderWithProviders, screen, waitFor } from "@/test-utils";
import { useEditorSession } from "@/hooks/useEditorSession";
import { EditorLayout } from "./EditorLayout";

let editorStoreModule: typeof import("@/stores/editorStore");

const manualSave = vi.fn();
const cancelUpload = vi.fn();
let mediaQueryMatches = false;
const uploadState = {
	cancelUpload,
	isUploading: false,
	totalCount: 0,
	failures: [] as unknown[],
	isCancelling: false,
};

vi.mock("@/hooks/useMediaQuery", () => ({
	useMediaQuery: () => mediaQueryMatches,
}));

vi.mock("@/hooks/useAutoSave", () => ({
	useAutoSave: () => ({ manualSave }),
}));

vi.mock("@/contexts/KeyboardContext", () => ({
	useCmdCtrlShortcut: vi.fn(),
}));

vi.mock("@/stores/uploadStore", () => ({
	useUploadStore: (selector: (state: typeof uploadState) => unknown) =>
		selector(uploadState),
}));

vi.mock("@/components/editor/StatusBar", () => ({
	StatusBar: () => <div data-testid="status-bar">Status bar</div>,
}));

vi.mock("@/components/editor/FileTabs", () => ({
	FileTabs: () => <div data-testid="file-tabs">File tabs</div>,
}));

vi.mock("@/components/file-tree", () => ({
	WorkspaceFileTree: () => (
		<div data-testid="workspace-tree">
			<button
				type="button"
				onClick={() => {
					editorStoreModule.useEditorStore.getState().openFileInTab(
						{
							name: "sample.tsx",
							path: "apps/design-review/sample.tsx",
							type: "file",
							size: 128,
							modified: "2026-09-05T12:00:00Z",
							extension: ".tsx",
							entity_type: null,
							entity_id: null,
						} as never,
						"console.log('sample')",
						"utf-8",
						"sample-etag",
					);
				}}
			>
				Open sample file
			</button>
		</div>
	),
}));

vi.mock("@/components/editor/CodeEditor", () => ({
	CodeEditor: () => {
		const { openFile } = useEditorSession();
		const [buffer, setBuffer] = useState("draft buffer");
		return (
			<div data-testid="code-pane">
				<div data-testid="code-path">{openFile?.path ?? "no-file"}</div>
				<input
					aria-label="code buffer"
					data-testid="code-buffer"
					value={buffer}
					onChange={(e) => setBuffer(e.target.value)}
				/>
			</div>
		);
	},
}));

vi.mock("@/components/editor/RunPanel", () => ({
	RunPanel: () => <div data-testid="run-panel">Run controls</div>,
}));

vi.mock("@/components/editor/SearchPanel", () => ({
	SearchPanel: () => <div data-testid="search-panel">Search</div>,
}));

vi.mock("@/components/editor/PackagePanel", () => ({
	PackagePanel: () => <div data-testid="packages-panel">Packages</div>,
}));

vi.mock("@/components/editor/SourceControlPanel", () => ({
	SourceControlPanel: () => <div data-testid="scm-panel">Source control</div>,
}));

vi.mock("@/components/editor/TerminalPanel", () => ({
	TerminalPanel: () => {
		const [buffer, setBuffer] = useState("terminal draft");
		return (
			<div data-testid="terminal-pane">
				<input
					aria-label="terminal buffer"
					data-testid="terminal-buffer"
					value={buffer}
					onChange={(e) => setBuffer(e.target.value)}
				/>
			</div>
		);
	},
}));

beforeAll(async () => {
	editorStoreModule = await import("@/stores/editorStore");
});

beforeEach(() => {
	mediaQueryMatches = false;
	manualSave.mockClear();
	cancelUpload.mockClear();
	uploadState.isUploading = false;
	uploadState.totalCount = 0;
	uploadState.failures = [];
	uploadState.isCancelling = false;
	editorStoreModule.useEditorStore.setState({
		tabs: [],
		activeTabIndex: -1,
		sidebarPanel: "files",
		layoutMode: "fullscreen",
		terminalHeight: 240,
		isOpen: true,
		isLoadingFile: false,
		diffPreview: null,
	});
});

describe("EditorLayout responsive shell", () => {
	it("keeps mobile panes mounted while switching between files, code, output, and run controls", async () => {
		const { user, rerender } = renderWithProviders(<EditorLayout />);

		expect(
			screen.getByRole("button", { name: "Files & Tools" }),
		).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Code" })).toBeDisabled();
		expect(screen.getAllByTestId("code-pane")).toHaveLength(1);
		expect(screen.getAllByTestId("terminal-pane")).toHaveLength(1);
		expect(
			screen.queryByRole("textbox", { name: "code buffer" }),
		).toBeNull();
		expect(screen.getByTestId("workspace-tree")).toBeInTheDocument();

		await user.click(
			screen.getByRole("button", { name: "Open sample file" }),
		);
		await waitFor(() => {
			expect(screen.getByTestId("code-path")).toHaveTextContent(
				"apps/design-review/sample.tsx",
			);
		});

		expect(
			screen.getByRole("textbox", { name: "code buffer" }),
		).toBeInTheDocument();
		const codeBuffer = screen.getByTestId(
			"code-buffer",
		) as HTMLInputElement;
		await user.clear(codeBuffer);
		await user.type(codeBuffer, "preserved code draft");
		expect(codeBuffer).toHaveValue("preserved code draft");

		await user.click(screen.getByRole("button", { name: "Output" }));
		expect(
			screen.getByRole("textbox", { name: "terminal buffer" }),
		).toBeInTheDocument();
		const terminalBuffer = screen.getByTestId(
			"terminal-buffer",
		) as HTMLInputElement;
		await user.clear(terminalBuffer);
		await user.type(terminalBuffer, "terminal draft preserved");
		expect(terminalBuffer).toHaveValue("terminal draft preserved");

		window.dispatchEvent(new Event("run-editor-file"));
		await waitFor(() => {
			expect(screen.getAllByTestId("run-panel")).toHaveLength(1);
		});
		expect(
			screen.queryByRole("textbox", { name: "terminal buffer" }),
		).toBeNull();

		await user.click(screen.getByRole("button", { name: "Code" }));
		expect(
			screen.getByRole("textbox", { name: "code buffer" }),
		).toBeInTheDocument();
		expect(screen.getByTestId("code-buffer")).toHaveValue(
			"preserved code draft",
		);

		await user.click(screen.getByRole("button", { name: "Output" }));
		expect(
			screen.getByRole("textbox", { name: "terminal buffer" }),
		).toBeInTheDocument();
		expect(screen.getByTestId("terminal-buffer")).toHaveValue(
			"terminal draft preserved",
		);

		mediaQueryMatches = true;
		rerender(<EditorLayout />);
		expect(screen.getAllByTestId("code-pane")).toHaveLength(1);
		expect(screen.getAllByTestId("terminal-pane")).toHaveLength(1);
		expect(screen.getByTestId("code-buffer")).toHaveValue(
			"preserved code draft",
		);
		expect(screen.getByTestId("terminal-buffer")).toHaveValue(
			"terminal draft preserved",
		);
	});
});

it("returns to Files & Tools after closing the last file on mobile", async () => {
	const { user } = renderWithProviders(<EditorLayout />);
	await user.click(screen.getByRole("button", { name: "Open sample file" }));
	await waitFor(() =>
		expect(screen.getByRole("button", { name: "Code" })).toHaveAttribute(
			"aria-pressed",
			"true",
		),
	);
	act(() => editorStoreModule.useEditorStore.getState().closeAllTabs());
	await waitFor(() =>
		expect(
			screen.getByRole("button", { name: "Files & Tools" }),
		).toHaveAttribute("aria-pressed", "true"),
	);
	expect(screen.getByRole("button", { name: "Code" })).toBeDisabled();
	expect(screen.getByTestId("workspace-tree")).toBeVisible();
});

it("protects drafts in inactive tabs when closing the editor and restores focus on cancellation", async () => {
	const { user } = renderWithProviders(<EditorLayout />);
	await user.click(screen.getByRole("button", { name: "Open sample file" }));
	act(() => {
		const store = editorStoreModule.useEditorStore.getState();
		store.setFileContent("unsaved draft");
		store.openFileInTab(
			{ ...store.tabs[0].file, name: "other.tsx", path: "other.tsx" },
			"saved",
			"utf-8",
			"other-etag",
		);
	});
	const close = screen.getByRole("button", { name: "Close editor" });
	await user.click(close);
	expect(
		screen.getByRole("list", { name: "Files with unsaved changes" }),
	).toHaveTextContent("apps/design-review/sample.tsx");
	expect(editorStoreModule.useEditorStore.getState().isOpen).toBe(true);
	await user.click(screen.getByRole("button", { name: "Keep editing" }));
	await waitFor(() => expect(close).toHaveFocus());
	expect(editorStoreModule.useEditorStore.getState().tabs[0].content).toBe(
		"unsaved draft",
	);
	await user.click(close);
	await user.click(
		screen.getByRole("button", { name: "Discard changes and close" }),
	);
	expect(editorStoreModule.useEditorStore.getState().isOpen).toBe(false);
	expect(editorStoreModule.useEditorStore.getState().tabs).toHaveLength(0);
	expect(cancelUpload).not.toHaveBeenCalled();
});

it("waits for saving to finish and explains upload cancellation alongside unsaved changes", async () => {
	uploadState.isUploading = true;
	const { user } = renderWithProviders(<EditorLayout />);
	await user.click(screen.getByRole("button", { name: "Open sample file" }));
	act(() => {
		const store = editorStoreModule.useEditorStore.getState();
		store.setFileContent("draft");
		store.setSaveState(0, "saving");
	});
	await user.click(screen.getByRole("button", { name: "Close editor" }));
	expect(screen.getByRole("button", { name: "Saving…" })).toBeDisabled();
	expect(
		screen.getByText(/Files already uploaded will remain/),
	).toBeVisible();
	expect(cancelUpload).not.toHaveBeenCalled();
	act(() =>
		editorStoreModule.useEditorStore.getState().setSaveState(0, "dirty"),
	);
	await user.click(
		screen.getByRole("button", { name: "Discard changes and close" }),
	);
	expect(cancelUpload).toHaveBeenCalledTimes(1);
	expect(editorStoreModule.useEditorStore.getState().isOpen).toBe(false);
});

it("closes a clean editor immediately", async () => {
	const { user } = renderWithProviders(<EditorLayout />);
	await user.click(screen.getByRole("button", { name: "Open sample file" }));
	await user.click(screen.getByRole("button", { name: "Close editor" }));
	expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
	expect(editorStoreModule.useEditorStore.getState().isOpen).toBe(false);
});

it("opens a mobile comparison without a file tab and returns to tools when closed", () => {
 renderWithProviders(<EditorLayout />);
 act(() => editorStoreModule.useEditorStore.getState().setDiffPreview({path:"workflow.py",displayName:"Workflow",entityType:"workflow",localContent:"local",remoteContent:"remote",isConflict:true}));
 expect(screen.getByRole("button",{name:"Code"})).toBeEnabled();
 expect(screen.getByRole("button",{name:"Code"})).toHaveAttribute("aria-pressed","true");
 act(() => editorStoreModule.useEditorStore.getState().clearDiffPreview());
 expect(screen.getByRole("button",{name:"Code"})).toBeDisabled();
 expect(screen.getByRole("button",{name:"Files & Tools"})).toHaveAttribute("aria-pressed","true");
});
