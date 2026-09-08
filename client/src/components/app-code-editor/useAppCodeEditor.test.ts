import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useAppCodeEditor } from "./useAppCodeEditor";

describe("app editor save recovery", () => {
	it("loads saved source cleanly without marking it dirty", () => {
		const { result } = renderHook(() =>
			useAppCodeEditor({
				initialSource: "original",
				initialCompiled: "compiled",
			}),
		);
		act(() => result.current.setSource("edited"));
		expect(result.current.state).toMatchObject({
			source: "edited",
			hasUnsavedChanges: true,
		});
		act(() => result.current.loadSource("fresh", "new-compiled"));
		expect(result.current.state).toMatchObject({
			source: "fresh",
			compiled: "new-compiled",
			hasUnsavedChanges: false,
			isCompiling: false,
			saveError: null,
			errors: [],
		});
	});

	it("retains a failed draft and allows retry without compilation errors", async () => {
		const onSave = vi
			.fn()
			.mockRejectedValueOnce(new Error("Connection lost"))
			.mockResolvedValueOnce(undefined);
		const { result } = renderHook(() =>
			useAppCodeEditor({ initialSource: "original", onSave }),
		);
		act(() => result.current.setSource("edited"));
		await act(() => result.current.save());
		expect(result.current.state).toMatchObject({
			source: "edited",
			hasUnsavedChanges: true,
			saveError: "Connection lost",
			errors: [],
			isCompiling: false,
		});
		await act(() => result.current.save());
		expect(onSave).toHaveBeenLastCalledWith("edited", "edited");
		expect(result.current.state).toMatchObject({
			hasUnsavedChanges: false,
			saveError: null,
		});
	});

	it("keeps edits made during an outstanding save dirty and prevents duplicate saves", async () => {
		let finish!: () => void;
		const onSave = vi.fn(
			() =>
				new Promise<void>((resolve) => {
					finish = resolve;
				}),
		);
		const { result } = renderHook(() =>
			useAppCodeEditor({ initialSource: "original", onSave }),
		);
		act(() => result.current.setSource("first edit"));
		let pending!: Promise<void>;
		act(() => {
			pending = result.current.save();
		});
		act(() => result.current.setSource("newer edit"));
		await act(() => result.current.save());
		expect(onSave).toHaveBeenCalledTimes(1);
		await act(async () => {
			finish();
			await pending;
		});
		expect(result.current.state).toMatchObject({
			source: "newer edit",
			hasUnsavedChanges: true,
			isCompiling: false,
		});
	});
});
