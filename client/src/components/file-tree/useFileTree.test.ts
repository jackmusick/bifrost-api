import { act, renderHook } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { useFileTree } from "./useFileTree";
import type { FileOperations, FileNode } from "./types";

const file: FileNode = {
	path: "test.py",
	name: "test.py",
	type: "file",
	extension: "py",
	size: null,
	modified: "2026-09-07",
};
function setup() {
	const operations: FileOperations = {
		list: vi.fn(async () => [file]),
		read: vi.fn(),
		write: vi.fn(),
		delete: vi.fn(),
		rename: vi.fn(),
		createFolder: vi.fn(),
	};
	return { operations, ...renderHook(() => useFileTree(operations)) };
}
it("reports failed root reads until a retry succeeds", async () => {
	const { result, operations } = setup();
	vi.mocked(operations.list).mockRejectedValueOnce(new Error("Offline"));
	await act(() => result.current.loadFiles(""));
	expect(result.current.failedPaths).toEqual([""]);
	await act(() => result.current.loadFiles(""));
	expect(result.current.failedPaths).toEqual([]);
	expect(result.current.files.map((f) => f.path)).toEqual(["test.py"]);
});
it("preserves cached files during refresh and after refresh failure", async () => {
	const { result, operations } = setup();
	await act(() => result.current.loadFiles(""));
	let rejectRefresh!: (error: Error) => void;
	vi.mocked(operations.list).mockImplementationOnce(
		() =>
			new Promise((_, reject) => {
				rejectRefresh = reject;
			}),
	);
	let refresh!: Promise<void>;
	act(() => {
		refresh = result.current.refreshAll();
	});
	expect(result.current.isLoading).toBe(true);
	expect(result.current.files.map((f) => f.path)).toEqual(["test.py"]);
	await act(async () => {
		rejectRefresh(new Error("Offline"));
		await refresh;
	});
	expect(result.current.files.map((f) => f.path)).toEqual(["test.py"]);
	expect(result.current.failedPaths).toEqual([""]);
	expect(result.current.isLoading).toBe(false);
});
