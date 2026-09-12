import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSaveQueue } from "./useSaveQueue";
import { fileService } from "@/services/fileService";
vi.mock("@/services/fileService", () => ({
	fileService: { writeFile: vi.fn() },
	FileConflictError: class extends Error {},
}));
vi.mock("sonner", () => ({ toast: { error: vi.fn() } }));
beforeEach(() => {
	vi.useFakeTimers();
	vi.clearAllMocks();
});
afterEach(() => {
	vi.useRealTimers();
});

describe("useSaveQueue closed files", () => {
	it("discards a closed file's queued edit while saving remaining open files", async () => {
		const open = new Set(["closed.py", "open.py"]);
		vi.mocked(fileService.writeFile).mockResolvedValue({
			etag: "new",
			content: "kept",
		} as Awaited<ReturnType<typeof fileService.writeFile>>);
		const { result } = renderHook(() =>
			useSaveQueue((path) => open.has(path)),
		);
		act(() => {
			result.current.enqueueSave("closed.py", "discarded");
			result.current.enqueueSave("open.py", "kept");
		});
		open.delete("closed.py");
		await act(async () => {
			await vi.advanceTimersByTimeAsync(1000);
		});
		expect(fileService.writeFile).toHaveBeenCalledTimes(1);
		expect(vi.mocked(fileService.writeFile).mock.calls[0][0]).toBe(
			"open.py",
		);
		expect(result.current.getPendingCount()).toBe(0);
	});
	it("does not apply a late completion callback to a closed tab", async () => {
		let open = true;
		let finish!: (
			value: Awaited<ReturnType<typeof fileService.writeFile>>,
		) => void;
		vi.mocked(fileService.writeFile).mockReturnValue(
			new Promise((resolve) => {
				finish = resolve;
			}),
		);
		const complete = vi.fn();
		const { result } = renderHook(() => useSaveQueue(() => open));
		act(() =>
			result.current.enqueueSave(
				"closed.py",
				"draft",
				"utf-8",
				undefined,
				complete,
			),
		);
		await act(async () => {
			await vi.advanceTimersByTimeAsync(1000);
		});
		open = false;
		await act(async () => {
			finish({ etag: "new" } as Awaited<
				ReturnType<typeof fileService.writeFile>
			>);
		});
		expect(complete).not.toHaveBeenCalled();
		expect(result.current.getPendingCount()).toBe(0);
	});
});

it("notifies an open file of save failure so its UI can leave saving state", async () => {
	const log = vi.spyOn(console, "error").mockImplementation(() => {});
	vi.mocked(fileService.writeFile).mockRejectedValueOnce(
		new Error("Save rejected"),
	);
	const failed = vi.fn();
	const { result } = renderHook(() => useSaveQueue(() => true));
	act(() =>
		result.current.enqueueSave(
			"open.py",
			"draft",
			"utf-8",
			undefined,
			undefined,
			undefined,
			false,
			failed,
		),
	);
	await act(async () => {
		await vi.advanceTimersByTimeAsync(1000);
	});
	expect(failed).toHaveBeenCalledTimes(1);
	expect(result.current.getPendingCount()).toBe(0);
	log.mockRestore();
});

it("retains an edit queued during a save and uses the resulting etag for its write", async () => {
	let finishFirst!: (
		value: Awaited<ReturnType<typeof fileService.writeFile>>,
	) => void;
	vi.mocked(fileService.writeFile)
		.mockReturnValueOnce(
			new Promise((resolve) => {
				finishFirst = resolve;
			}),
		)
		.mockResolvedValueOnce({ etag: "third" } as Awaited<
			ReturnType<typeof fileService.writeFile>
		>);
	const oldComplete = vi.fn();
	const newComplete = vi.fn();
	const { result } = renderHook(() => useSaveQueue());
	act(() =>
		result.current.enqueueSave(
			"open.py",
			"first edit",
			"utf-8",
			"first",
			oldComplete,
		),
	);
	await act(async () => {
		await vi.advanceTimersByTimeAsync(1000);
	});
	act(() =>
		result.current.enqueueSave(
			"open.py",
			"second edit",
			"utf-8",
			"first",
			newComplete,
		),
	);
	await act(async () => {
		await vi.advanceTimersByTimeAsync(1000);
	});
	await act(async () => {
		finishFirst({ etag: "second" } as Awaited<
			ReturnType<typeof fileService.writeFile>
		>);
	});
	expect(fileService.writeFile).toHaveBeenCalledTimes(2);
	expect(vi.mocked(fileService.writeFile).mock.calls[1].slice(0, 4)).toEqual([
		"open.py",
		"second edit",
		"utf-8",
		"second",
	]);
	expect(oldComplete).not.toHaveBeenCalled();
	expect(newComplete).toHaveBeenCalledWith(
		"third",
		undefined,
		false,
		undefined,
	);
	expect(result.current.getPendingCount()).toBe(0);
});
