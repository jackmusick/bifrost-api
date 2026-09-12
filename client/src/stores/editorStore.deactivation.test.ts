import { afterEach, expect, it, vi } from "vitest";
import { useEditorStore } from "./editorStore";
import { fileService } from "@/services/fileService";
afterEach(() => {
	vi.restoreAllMocks();
	useEditorStore.setState({ pendingDeactivationConflict: null });
});
it("preserves conflict and source draft while pending and after a failed resolution", async () => {
	const conflict = {
		pendingDeactivations: [],
		availableReplacements: [],
		filePath: "synthetic.py",
		content: "retained draft",
		encoding: "utf-8" as const,
		tabIndex: 0,
	};
	useEditorStore.setState({ pendingDeactivationConflict: conflict });
	let fail: (reason: Error) => void = () => {};
	const write = vi.spyOn(fileService, "writeFile").mockImplementationOnce(
		() =>
			new Promise((_, reject) => {
				fail = reject;
			}),
	);
	vi.spyOn(console, "error").mockImplementation(() => {});
	const result = useEditorStore
		.getState()
		.resolveDeactivationConflict("apply", { a: "replacement" }, ["b"]);
	expect(useEditorStore.getState().pendingDeactivationConflict).toBe(
		conflict,
	);
	fail(new Error("Unavailable"));
	await expect(result).resolves.toBeNull();
	expect(useEditorStore.getState().pendingDeactivationConflict).toBe(
		conflict,
	);
	expect(write).toHaveBeenCalledWith(
		"synthetic.py",
		"retained draft",
		"utf-8",
		undefined,
		false,
		undefined,
		false,
		{ a: "replacement" },
		["b"],
	);
	await useEditorStore.getState().resolveDeactivationConflict("cancel");
	expect(useEditorStore.getState().pendingDeactivationConflict).toBeNull();
	expect(write).toHaveBeenCalledTimes(1);
});
