import { afterEach, describe, expect, it } from "vitest";
import { useEditorStore } from "./editorStore";
afterEach(() => useEditorStore.setState({ tabs: [], activeTabIndex: -1 }));
describe("editor content notifications", () => {
	it("does not clear unsaved changes when Monaco repeats the current value", () => {
		useEditorStore.getState().openFileInTab({ name: "draft.py", path: "draft.py", type: "file", modified: "2026-09-06T12:00:00Z" }, "original", "utf-8", "etag");
		useEditorStore.getState().setFileContent("edited");
		expect(useEditorStore.getState().tabs[0].unsavedChanges).toBe(true);
		useEditorStore.getState().setFileContent("edited");
		expect(useEditorStore.getState().tabs[0].unsavedChanges).toBe(true);
		useEditorStore.getState().markSaved();
		useEditorStore.getState().setFileContent("edited");
		expect(useEditorStore.getState().tabs[0].unsavedChanges).toBe(false);
	});
});
