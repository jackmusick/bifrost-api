import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { DeleteConfirmation } from "./DeleteConfirmation";
import { files } from "@/lib/app-sdk/files";
import { deleteFilePolicy } from "@/services/filePolicies";
vi.mock("@/lib/app-sdk/files", () => ({ files: { delete: vi.fn() } }));
vi.mock("@/services/filePolicies", () => ({ deleteFilePolicy: vi.fn() }));

describe("DeleteConfirmation", () => {
	beforeEach(() => vi.resetAllMocks());
	it("does not delete on open or cancel", () => {
		const onClose = vi.fn();
		render(
			<DeleteConfirmation
				target={{
					kind: "file",
					location: "gallery",
					scope: "org-1",
					path: "reports/a.txt",
				}}
				onClose={onClose}
				onDeleted={vi.fn()}
				onRestoreFocus={vi.fn()}
			/>,
		);
		expect(screen.getByText("reports/a.txt")).toBeInTheDocument();
		fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
		expect(files.delete).not.toHaveBeenCalled();
		expect(onClose).toHaveBeenCalled();
	});
	it("guards pending deletion, retains failures, and retries the captured target", async () => {
		let reject!: (error: Error) => void;
		vi.mocked(files.delete)
			.mockReturnValueOnce(
				new Promise((_, fail) => {
					reject = fail;
				}),
			)
			.mockResolvedValue(undefined);
		const onClose = vi.fn(),
			onDeleted = vi.fn();
		const target = {
			kind: "file" as const,
			location: "gallery",
			scope: "org-1",
			path: "reports/a.txt",
		};
		render(
			<DeleteConfirmation
				target={target}
				onClose={onClose}
				onDeleted={onDeleted}
				onRestoreFocus={vi.fn()}
			/>,
		);
		fireEvent.click(screen.getByRole("button", { name: "Delete file" }));
		expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
		fireEvent.keyDown(screen.getByRole("alertdialog"), { key: "Escape" });
		expect(onClose).not.toHaveBeenCalled();
		reject(new Error("Unavailable"));
		expect(await screen.findByRole("alert")).toHaveTextContent(
			"Couldn’t delete this file",
		);
		expect(onDeleted).not.toHaveBeenCalled();
		fireEvent.click(screen.getByRole("button", { name: "Retry delete" }));
		await waitFor(() => expect(onDeleted).toHaveBeenCalledWith(target));
		expect(files.delete).toHaveBeenNthCalledWith(2, "reports/a.txt", {
			location: "gallery",
			scope: "org-1",
		});
		expect(onClose).toHaveBeenCalledOnce();
	});
	it("deletes only the policy and preserves its full scope contract", async () => {
		vi.mocked(deleteFilePolicy).mockResolvedValue(undefined);
		const policy = {
			location: "gallery",
			path: "",
			organizationId: "org-2",
			policies: { policies: [] },
		};
		const onDeleted = vi.fn();
		render(
			<DeleteConfirmation
				target={{ kind: "policy", policy }}
				onClose={vi.fn()}
				onDeleted={onDeleted}
				onRestoreFocus={vi.fn()}
			/>,
		);
		expect(screen.getByText(/Files will remain/)).toBeInTheDocument();
		fireEvent.click(screen.getByRole("button", { name: "Delete policy" }));
		await waitFor(() => expect(onDeleted).toHaveBeenCalled());
		expect(deleteFilePolicy).toHaveBeenCalledWith(policy);
		expect(files.delete).not.toHaveBeenCalled();
	});
});
