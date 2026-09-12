import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { EditorUploadStatus } from "./EditorUploadStatus";
import type { UploadState } from "@/stores/uploadStore";
const base: UploadState = { isUploading: true, isCancelling: false, isCancelled: false, currentFile: "folder/full-file-name.py", completedCount: 1, totalCount: 3, failures: [] };

describe("EditorUploadStatus", () => {
	it("exposes progress and cancel, then disables cancellation while pending", async () => {
		const user = userEvent.setup();
		const onCancel = vi.fn();
		const onDismiss = vi.fn();
		const { rerender } = render(<EditorUploadStatus state={base} onCancel={onCancel} onDismiss={onDismiss} />);
		expect(screen.getByText(base.currentFile!)).toBeVisible();
		expect(screen.getByRole("progressbar", { name: "File upload progress" })).toHaveAttribute("aria-valuenow", "33");
		await user.click(screen.getByRole("button", { name: "Cancel upload" }));
		expect(onCancel).toHaveBeenCalledTimes(1);
		rerender(<EditorUploadStatus state={{ ...base, isCancelling: true }} onCancel={onCancel} onDismiss={onDismiss} />);
		expect(screen.getByRole("button")).toBeDisabled();
		expect(screen.getByRole("status")).toHaveTextContent("Cancelling upload");
	});
	it("shows cancellation and inspectable failures without claiming all files uploaded", async () => {
		const user = userEvent.setup();
		const onDismiss = vi.fn();
		render(<EditorUploadStatus state={{ ...base, isUploading: false, isCancelled: true, failures: [{ path: "folder/failed.py", error: "Permission denied" }] }} onCancel={vi.fn()} onDismiss={onDismiss} />);
		expect(screen.getByRole("status")).toHaveTextContent("Upload cancelled");
		await user.click(screen.getByText("Review 1 failed file"));
		expect(screen.getByText("folder/failed.py")).toBeVisible();
		expect(screen.getByText("Permission denied")).toBeVisible();
		await user.click(screen.getByRole("button", { name: "Dismiss upload status" }));
		expect(onDismiss).toHaveBeenCalledTimes(1);
	});
});
