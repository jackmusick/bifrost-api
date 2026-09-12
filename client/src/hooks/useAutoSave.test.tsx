import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAutoSave } from "./useAutoSave";

const shared = vi.hoisted(() => {
	const enqueueSaveMock = vi.fn();
	const waitForPendingSavesMock = vi.fn();
	const reloadWorkflowFileMock = vi.fn();
	const writeFileMock = vi.fn();

	const editorStore = {
		tabs: [] as TestTab[],
		activeTabIndex: 0,
		setSaveState: vi.fn(),
		setConflictState: vi.fn(),
		setDiagnostics: vi.fn(),
		setIndexing: vi.fn(),
		updateTabContent: vi.fn(),
		setPendingWorkflowConflict: vi.fn(),
		setPendingDeactivationConflict: vi.fn(),
	};

	editorStore.setSaveState = vi.fn((tabIndex: number, state: SaveState) => {
		const tab = editorStore.tabs[tabIndex];
		if (tab) {
			tab.saveState = state;
		}
	});
	editorStore.setConflictState = vi.fn();
	editorStore.setDiagnostics = vi.fn(
		(tabIndex: number, diagnostics: unknown) => {
			const tab = editorStore.tabs[tabIndex];
			if (tab) {
				tab.diagnostics = diagnostics;
			}
		},
	);
	editorStore.setIndexing = vi.fn();
	editorStore.updateTabContent = vi.fn(
		(tabIndex: number, content: string, etag: string) => {
			const tab = editorStore.tabs[tabIndex];
			if (tab) {
				tab.content = content;
				tab.etag = etag;
				tab.unsavedChanges = false;
				tab.saveState = "saved";
			}
		},
	);
	editorStore.setPendingWorkflowConflict = vi.fn();
	editorStore.setPendingDeactivationConflict = vi.fn();

	const useEditorStoreMock = Object.assign(
		(selector: (state: typeof editorStore) => unknown) =>
			selector(editorStore),
		{
			getState: () => editorStore,
			setState: (partial: Record<string, unknown>) => {
				Object.assign(editorStore, partial);
			},
		},
	);

	return {
		enqueueSaveMock,
		waitForPendingSavesMock,
		reloadWorkflowFileMock,
		writeFileMock,
		editorStore,
		useEditorStoreMock,
	};
});

vi.mock("@/stores/editorStore", () => ({
	useEditorStore: shared.useEditorStoreMock,
}));

vi.mock("./useSaveQueue", () => ({
	useSaveQueue: () => ({
		enqueueSave: (...args: unknown[]) => shared.enqueueSaveMock(...args),
		waitForPendingSaves: (...args: unknown[]) =>
			shared.waitForPendingSavesMock(...args),
	}),
}));

vi.mock("./useWorkflows", () => ({
	useReloadWorkflowFile: () => ({ mutate: shared.reloadWorkflowFileMock }),
}));

vi.mock("@/services/fileService", () => ({
	fileService: { writeFile: shared.writeFileMock },
	FileConflictError: class extends Error {},
}));

vi.mock("sonner", () => ({ toast: { error: vi.fn() } }));

type SaveState = "clean" | "dirty" | "saving" | "saved" | "conflict";

type TestTab = {
	file: { name: string; path: string };
	content: string;
	encoding: "utf-8";
	unsavedChanges: boolean;
	saveState?: SaveState;
	etag?: string;
	diagnostics?: unknown;
};

function makeTab(path: string, overrides: Partial<TestTab> = {}): TestTab {
	return {
		file: { name: path.split("/").pop() ?? path, path },
		content: overrides.content ?? "draft",
		encoding: "utf-8",
		unsavedChanges: overrides.unsavedChanges ?? true,
		saveState: overrides.saveState ?? "dirty",
		etag: overrides.etag,
		diagnostics: overrides.diagnostics,
	};
}

beforeEach(() => {
	vi.useFakeTimers();
	vi.clearAllMocks();
	shared.editorStore.tabs = [];
	shared.editorStore.activeTabIndex = 0;
});

afterEach(() => {
	vi.useRealTimers();
});

describe("useAutoSave", () => {
	it("resolves save completion and delayed state transitions against the reordered tab", async () => {
		shared.editorStore.tabs = [
			makeTab("alpha.py", { content: "alpha", saveState: "dirty" }),
			makeTab("beta.py", {
				content: "beta",
				unsavedChanges: false,
				saveState: "clean",
			}),
		];
		shared.editorStore.activeTabIndex = 0;

		renderHook(() => useAutoSave());

		await act(async () => {});
		expect(shared.enqueueSaveMock).toHaveBeenCalledTimes(1);
		const onComplete = shared.enqueueSaveMock.mock.calls[0]?.[4] as
			| ((
					newEtag: string,
					newContent?: string,
					needsIndexing?: boolean,
					diagnostics?: Array<{ severity: "info"; message: string }>,
			  ) => void)
			| undefined;
		expect(onComplete).toBeTypeOf("function");

		shared.editorStore.tabs = [
			shared.editorStore.tabs[1],
			shared.editorStore.tabs[0],
		];
		shared.editorStore.activeTabIndex = 0;

		const diagnostics = [{ severity: "info" as const, message: "saved" }];
		const saveStateCalls = shared.editorStore.setSaveState.mock
			.calls as Array<[number, string]>;

		await act(async () => {
			await vi.advanceTimersByTimeAsync(950);
		});
		expect(
			saveStateCalls.filter(
				([index, state]) => index === 1 && state === "saving",
			),
		).toHaveLength(1);

		await act(async () => {
			onComplete?.("etag-1", "saved content", false, diagnostics);
		});

		expect(shared.editorStore.setDiagnostics).toHaveBeenCalledWith(
			1,
			diagnostics,
		);
		expect(shared.editorStore.updateTabContent).toHaveBeenCalledWith(
			1,
			"saved content",
			"etag-1",
		);

		await act(async () => {
			await vi.advanceTimersByTimeAsync(2500);
		});

		expect(
			saveStateCalls.filter(
				([index, state]) => index === 1 && state === "clean",
			),
		).toHaveLength(1);
		expect(
			saveStateCalls.filter(
				([index, state]) => index === 0 && state === "saving",
			),
		).toHaveLength(0);
		expect(
			saveStateCalls.filter(
				([index, state]) => index === 0 && state === "clean",
			),
		).toHaveLength(0);
	});

	it("skips save completion and delayed transitions after the tab closes", async () => {
		shared.editorStore.tabs = [
			makeTab("alpha.py", { content: "alpha", saveState: "dirty" }),
			makeTab("beta.py", {
				content: "beta",
				unsavedChanges: false,
				saveState: "clean",
			}),
		];
		shared.editorStore.activeTabIndex = 0;

		renderHook(() => useAutoSave());

		await act(async () => {});
		expect(shared.enqueueSaveMock).toHaveBeenCalledTimes(1);
		const onComplete = shared.enqueueSaveMock.mock.calls[0]?.[4] as
			| ((
					newEtag: string,
					newContent?: string,
					needsIndexing?: boolean,
					diagnostics?: Array<{ severity: "info"; message: string }>,
			  ) => void)
			| undefined;
		expect(onComplete).toBeTypeOf("function");

		shared.editorStore.tabs = [shared.editorStore.tabs[1]];
		shared.editorStore.activeTabIndex = 0;

		await act(async () => {
			await vi.advanceTimersByTimeAsync(950);
		});
		const saveStateCalls = shared.editorStore.setSaveState.mock
			.calls as Array<[number, string]>;

		expect(
			saveStateCalls.filter(
				([index, state]) => index === 0 && state === "saving",
			),
		).toHaveLength(0);

		await act(async () => {
			onComplete?.("etag-1", "saved content", false, [
				{ severity: "info", message: "saved" },
			]);
		});

		expect(shared.editorStore.setDiagnostics).not.toHaveBeenCalled();
		expect(shared.editorStore.updateTabContent).not.toHaveBeenCalled();

		await act(async () => {
			await vi.advanceTimersByTimeAsync(2500);
		});

		expect(
			saveStateCalls.filter(
				([index, state]) => index === 0 && state === "clean",
			),
		).toHaveLength(0);
	});
});

it("applies manual indexing results to the original file after tabs reorder during the request", async () => {
	const alpha = makeTab("alpha.py", { content: "alpha", etag: "before" });
	const beta = makeTab("beta.py", {
		content: "beta",
		unsavedChanges: false,
		saveState: "clean",
	});
	shared.editorStore.tabs = [alpha, beta];
	let finishIndex!: (response: {
		etag: string;
		content: string;
		content_modified: boolean;
	}) => void;
	shared.writeFileMock
		.mockResolvedValueOnce({ etag: "saved", needs_indexing: true })
		.mockImplementationOnce(
			() =>
				new Promise((resolve) => {
					finishIndex = resolve;
				}),
		);
	const { result } = renderHook(() => useAutoSave());
	let saving!: Promise<void>;
	await act(async () => {
		saving = result.current.manualSave();
	});
	expect(shared.writeFileMock).toHaveBeenCalledTimes(2);
	shared.editorStore.tabs = [
		shared.editorStore.tabs[1],
		shared.editorStore.tabs[0],
	];
	await act(async () => {
		finishIndex({
			etag: "indexed",
			content: "alpha with workflow id",
			content_modified: true,
		});
		await saving;
	});
	expect(shared.editorStore.updateTabContent).toHaveBeenCalledWith(
		1,
		"alpha with workflow id",
		"indexed",
	);
	expect(shared.editorStore.tabs[0].content).toBe("beta");
	expect(shared.editorStore.tabs[0].saveState).toBe("clean");
});
