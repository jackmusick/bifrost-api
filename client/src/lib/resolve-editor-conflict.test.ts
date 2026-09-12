import { afterEach, expect, it, vi } from "vitest";
import { fileService } from "@/services/fileService";
import { useEditorStore } from "@/stores/editorStore";
import { resolveEditorConflict } from "./resolve-editor-conflict";
vi.mock("@/services/fileService", () => ({
	fileService: { writeFile: vi.fn() },
}));
const conflict = {
	current_content: "server",
	incoming_content: "local",
	current_etag: "reviewed-etag",
	message: "Conflict",
};
const response = {
	path: "one.py",
	content: "local",
	encoding: "utf-8",
	size: 5,
	etag: "saved-etag",
	modified: "2026-09-06T12:00:00Z",
	content_modified: false,
	needs_indexing: false,
};
function seed() {
	useEditorStore
		.getState()
		.openFileInTab(
			{
				path: "one.py",
				name: "one.py",
				type: "file",
				modified: response.modified,
			},
			"local",
			"utf-8",
			"old-etag",
		);
	useEditorStore.setState((state) => ({
		tabs: state.tabs.map((tab) => ({
			...tab,
			gitConflict: conflict,
			unsavedChanges: true,
			saveState: "conflict" as const,
		})),
	}));
}
afterEach(() => {
	useEditorStore.setState({ tabs: [], activeTabIndex: -1 });
	vi.clearAllMocks();
});
it("checks the reviewed server etag and updates the originating tab after a tab switch", async () => {
	seed();
	let finish!: (result: typeof response) => void;
	vi.mocked(fileService.writeFile).mockReturnValueOnce(
		new Promise((resolve) => {
			finish = resolve;
		}),
	);
	const saving = resolveEditorConflict("one.py", conflict, "incoming");
	expect(fileService.writeFile).toHaveBeenCalledWith(
		"one.py",
		"local",
		"utf-8",
		"reviewed-etag",
	);
	useEditorStore
		.getState()
		.openFileInTab(
			{
				path: "two.py",
				name: "two.py",
				type: "file",
				modified: response.modified,
			},
			"unrelated",
			"utf-8",
			"two-etag",
		);
	finish(response);
	await saving;
	const { tabs, activeTabIndex } = useEditorStore.getState();
	expect(activeTabIndex).toBe(1);
	expect(tabs[1].content).toBe("unrelated");
	expect(tabs[1].etag).toBe("two-etag");
	expect(tabs[0]).toMatchObject({
		content: "local",
		etag: "saved-etag",
		unsavedChanges: false,
		saveState: "saved",
	});
	expect(tabs[0].gitConflict).toBeUndefined();
});
it("retains conflict and local edits when the conditional write fails", async () => {
	seed();
	vi.mocked(fileService.writeFile).mockRejectedValueOnce(
		new Error("Server changed again"),
	);
	await expect(
		resolveEditorConflict("one.py", conflict, "current"),
	).rejects.toThrow("Server changed again");
	expect(useEditorStore.getState().tabs[0]).toMatchObject({
		content: "local",
		gitConflict: conflict,
		unsavedChanges: true,
	});
});
it("preserves edits made while resolution saves", async () => {
	seed();
	let finish!: (result: typeof response) => void;
	vi.mocked(fileService.writeFile).mockReturnValueOnce(
		new Promise((resolve) => {
			finish = resolve;
		}),
	);
	const saving = resolveEditorConflict("one.py", conflict, "current");
	useEditorStore.getState().setFileContent("new local edit");
	finish({ ...response, content: "server" });
	await saving;
	expect(useEditorStore.getState().tabs[0]).toMatchObject({
		content: "new local edit",
		etag: "saved-etag",
		unsavedChanges: true,
		saveState: "dirty",
	});
});
it("does not clear a newer conflict on the same file", async () => {
	seed();
	let finish!: (result: typeof response) => void;
	vi.mocked(fileService.writeFile).mockReturnValueOnce(
		new Promise((resolve) => {
			finish = resolve;
		}),
	);
	const saving = resolveEditorConflict("one.py", conflict, "incoming");
	const newer = { ...conflict, current_etag: "newer-etag" };
	useEditorStore.setState((state) => ({
		tabs: state.tabs.map((tab) => ({ ...tab, gitConflict: newer })),
	}));
	finish(response);
	await saving;
	expect(useEditorStore.getState().tabs[0].gitConflict).toBe(newer);
	expect(useEditorStore.getState().tabs[0].etag).toBe("old-etag");
});

it("uses normalized content returned by the server", async () => {
	seed();
	vi.mocked(fileService.writeFile).mockResolvedValueOnce({
		...response,
		content: "normalized local",
		content_modified: true,
	});
	await resolveEditorConflict("one.py", conflict, "incoming");
	expect(useEditorStore.getState().tabs[0]).toMatchObject({
		content: "normalized local",
		etag: "saved-etag",
		unsavedChanges: false,
	});
});
