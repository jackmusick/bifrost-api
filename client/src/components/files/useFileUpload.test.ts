import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/app-sdk/files", () => ({ files: { upload: vi.fn() } }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
import { files } from "@/lib/app-sdk/files";
import { useFileUpload } from "./useFileUpload";

describe("useFileUpload", () => {
	beforeEach(() => vi.mocked(files.upload).mockReset());

	it("uploads each file to {prefix}/{name} then fires onUploaded", async () => {
		vi.mocked(files.upload).mockResolvedValue({
			url: "u",
			path: "p",
			expiresIn: 600,
		});
		const onUploaded = vi.fn();
		const { result } = renderHook(() =>
			useFileUpload("gallery", "global", "sub", onUploaded),
		);
		const a = new File(["x"], "a.png", { type: "image/png" });
		const b = new File(["y"], "b.png", { type: "image/png" });
		await act(async () => {
			await result.current.uploadFiles([a, b]);
		});
		expect(files.upload).toHaveBeenCalledWith("sub/a.png", a, {
			location: "gallery",
			scope: "global",
		});
		expect(files.upload).toHaveBeenCalledWith("sub/b.png", b, {
			location: "gallery",
			scope: "global",
		});
		expect(result.current.progress).toBeNull();
		expect(result.current.error).toBeNull();
		expect(result.current.pendingDestination).toBeNull();
		expect(typeof result.current.retryUpload).toBe("function");
		await waitFor(() => expect(onUploaded).toHaveBeenCalled());
	});

	it("is a no-op when location is null (read-only / no folder)", async () => {
		const onUploaded = vi.fn();
		const { result } = renderHook(() =>
			useFileUpload(null, "global", "", onUploaded),
		);
		await act(async () => {
			await result.current.uploadFiles([new File(["x"], "a.png")]);
		});
		expect(files.upload).not.toHaveBeenCalled();
		expect(onUploaded).not.toHaveBeenCalled();
		expect(result.current.uploading).toBe(false);
	});

	it("uploads to the bare name at the root (no prefix)", async () => {
		vi.mocked(files.upload).mockResolvedValue({
			url: "u",
			path: "p",
			expiresIn: 600,
		});
		const { result } = renderHook(() =>
			useFileUpload("gallery", null, "", vi.fn()),
		);
		const f = new File(["x"], "root.txt", { type: "text/plain" });
		await act(async () => {
			await result.current.uploadFiles([f]);
		});
		expect(files.upload).toHaveBeenCalledWith("root.txt", f, {
			location: "gallery",
			scope: null,
		});
	});

	it("retries the failed file and the remaining unattempted files from the original destination after a partial success", async () => {
		vi.mocked(files.upload)
			.mockResolvedValueOnce({
				url: "u",
				path: "sub/a.png",
				expiresIn: 600,
			})
			.mockRejectedValueOnce(new Error("boom"))
			.mockResolvedValueOnce({
				url: "u",
				path: "sub/b.png",
				expiresIn: 600,
			})
			.mockResolvedValueOnce({
				url: "u",
				path: "sub/c.png",
				expiresIn: 600,
			});
		const onUploaded = vi.fn();
		const { result, rerender } = renderHook(
			({
				location,
				prefix,
				scope,
			}: {
				location: string | null;
				prefix: string;
				scope: string;
			}) => useFileUpload(location, scope, prefix, onUploaded),
			{
				initialProps: {
					location: "gallery",
					prefix: "sub",
					scope: "global",
				},
			},
		);
		const a = new File(["x"], "a.png", { type: "image/png" });
		const b = new File(["y"], "b.png", { type: "image/png" });
		await act(async () => {
			await result.current.uploadFiles([a, b, new File(["z"], "c.png")]);
		});
		await waitFor(() =>
			expect(result.current.error).toContain(
				"Upload to gallery/sub failed at b.png",
			),
		);
		expect(result.current.uploading).toBe(false);
		expect(result.current.pendingDestination).toBe("sub/b.png");
		expect(onUploaded).toHaveBeenCalledTimes(1);

		rerender({
			location: "other",
			prefix: "new-prefix",
			scope: "other-org",
		});
		await act(async () => {
			result.current.retryUpload();
		});
		await waitFor(() => expect(onUploaded).toHaveBeenCalledTimes(2));
		expect(files.upload).toHaveBeenNthCalledWith(3, "sub/b.png", b, {
			location: "gallery",
			scope: "global",
		});
		expect(files.upload).toHaveBeenNthCalledWith(
			4,
			"sub/c.png",
			expect.any(File),
			{
				location: "gallery",
				scope: "global",
			},
		);
	});

	it("deduplicates files with the same upload target", async () => {
		vi.mocked(files.upload).mockResolvedValue({
			url: "u",
			path: "p",
			expiresIn: 600,
		});
		const { result } = renderHook(() =>
			useFileUpload("gallery", null, "sub", vi.fn()),
		);
		const file = new File(["x"], "dup.png", { type: "image/png" });
		await act(async () => {
			await result.current.uploadFiles([file, file]);
		});
		expect(files.upload).toHaveBeenCalledTimes(1);
		expect(files.upload).toHaveBeenCalledWith("sub/dup.png", file, {
			location: "gallery",
			scope: null,
		});
	});
	it("ignores duplicate submissions while a file is uploading", async () => {
		let finish!: (value: {
			url: string;
			path: string;
			expiresIn: number;
		}) => void;
		vi.mocked(files.upload).mockReturnValue(
			new Promise((resolve) => {
				finish = resolve;
			}),
		);
		const { result } = renderHook(() =>
			useFileUpload("gallery", "global", "sub", vi.fn()),
		);
		let pending!: Promise<void>;
		act(() => {
			pending = result.current.uploadFiles([new File(["x"], "one.txt")]);
		});
		expect(result.current.progress).toContain(
			"Uploading one.txt to gallery/sub",
		);
		await act(async () => {
			await result.current.uploadFiles([new File(["y"], "two.txt")]);
			result.current.retryUpload();
		});
		expect(files.upload).toHaveBeenCalledTimes(1);
		await act(async () => {
			finish({ url: "u", path: "sub/one.txt", expiresIn: 60 });
			await pending;
		});
		expect(result.current.uploading).toBe(false);
	});
});
