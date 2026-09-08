import {
	fireEvent,
	render,
	screen,
	waitFor,
	within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { toast } from "sonner";
import { FileTree } from "./FileTree";
import type { FileOperations } from "./types";

vi.mock("sonner", () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

function setup() {
	const file = {
		path: "test.py",
		name: "test.py",
		type: "file" as const,
		size: null,
		extension: "py",
		modified: "2026-09-07",
	};
	const folder = {
		path: "folder",
		name: "folder",
		type: "folder" as const,
		size: null,
		extension: null,
		modified: "2026-09-07",
	};
	const operations: FileOperations = {
		list: vi.fn(async () => [file, folder]),
		read: vi.fn(async () => ({ content: "", encoding: "utf-8" as const })),
		write: vi.fn(),
		createFolder: vi.fn(),
		delete: vi.fn(),
		rename: vi.fn(),
	};
	const editor = { onFileRenamed: vi.fn(), onFileDeleted: vi.fn() };
	render(<FileTree operations={operations} editor={editor} />);
	return { operations, editor, user: userEvent.setup() };
}

it("keeps the editor path after a failed rename, and updates it after retry succeeds", async () => {
	const { operations, editor, user } = setup();
	vi.mocked(operations.rename).mockRejectedValueOnce(
		new Error("Rename denied"),
	);
	await user.click(
		await screen.findByRole("button", { name: "Actions for test.py" }),
	);
	await user.click(screen.getByRole("menuitem", { name: "Rename" }));
	const input = screen.getByRole("textbox", { name: "Rename test.py" });
	await user.clear(input);
	await user.type(input, "renamed.py{Enter}");
	await waitFor(() =>
		expect(toast.error).toHaveBeenCalledWith(
			"Failed to rename",
			expect.anything(),
		),
	);
	expect(editor.onFileRenamed).not.toHaveBeenCalled();
	expect(input).toHaveValue("renamed.py");
	await waitFor(() => expect(input).toBeEnabled());
	await user.type(input, "{Enter}");
	await waitFor(() =>
		expect(editor.onFileRenamed).toHaveBeenCalledWith(
			"test.py",
			"renamed.py",
		),
	);
});

it("keeps editor tabs after a failed delete and notifies only after successful retry", async () => {
	const { operations, editor, user } = setup();
	vi.mocked(operations.delete).mockRejectedValueOnce(
		new Error("Delete denied"),
	);
	const remove = async () => {
		await user.click(
			await screen.findByRole("button", { name: "Actions for test.py" }),
		);
		await user.click(screen.getByRole("menuitem", { name: "Delete" }));
		await user.click(
			within(screen.getByRole("alertdialog")).getByRole("button", {
				name: "Delete",
			}),
		);
	};
	await remove();
	await waitFor(() =>
		expect(toast.error).toHaveBeenCalledWith(
			"Failed to delete",
			expect.anything(),
		),
	);
	expect(editor.onFileDeleted).not.toHaveBeenCalled();
	await remove();
	await waitFor(() =>
		expect(editor.onFileDeleted).toHaveBeenCalledWith("test.py", false),
	);
});

it("keeps editor paths after a rejected drag move", async () => {
	const { operations, editor } = setup();
	vi.mocked(operations.rename).mockRejectedValueOnce(
		new Error("Move denied"),
	);
	const target = await screen.findByRole("button", { name: "folder" });
	fireEvent.drop(target, {
		dataTransfer: { getData: () => "test.py", files: [] },
	});
	await waitFor(() =>
		expect(operations.rename).toHaveBeenCalledWith(
			"test.py",
			"folder/test.py",
		),
	);
	await waitFor(() =>
		expect(toast.error).toHaveBeenCalledWith(
			"Failed to move",
			expect.anything(),
		),
	);
	expect(editor.onFileRenamed).not.toHaveBeenCalled();
});

it("keeps the row action dropdown touch-friendly while preserving desktop density", async () => {
	const { user } = setup();
	await user.click(
		await screen.findByRole("button", { name: "Actions for test.py" }),
	);

	const renameItem = screen.getByRole("menuitem", { name: "Rename" });
	const deleteItem = screen.getByRole("menuitem", { name: "Delete" });

	expect(renameItem).toHaveClass("min-h-11");
	expect(renameItem).toHaveClass("sm:min-h-7");
	expect(deleteItem).toHaveClass("min-h-11");
	expect(deleteItem).toHaveClass("sm:min-h-7");
});
