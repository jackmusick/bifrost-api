import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { FilesInspector } from "./FilesInspector";

it("keeps file details in the workspace and closes with Escape", async () => {
	const user = userEvent.setup();
	const onClose = vi.fn();
	const { container } = render(
		<FilesInspector
			title="notes.txt"
			path="documents/notes.txt"
			isFile
			inline
			onClose={onClose}
		>
			<p>Preview content</p>
		</FilesInspector>,
	);
	const pane = screen.getByRole("region", { name: "File details" });
	expect(container).toContainElement(pane);
	expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
	expect(pane).toHaveTextContent("documents/notes.txt");
	expect(
		screen.getByRole("button", { name: "Close file details" }),
	).toHaveFocus();
	await user.keyboard("{Escape}");
	expect(onClose).toHaveBeenCalledOnce();
});

it("uses the same contained controls in the narrow workspace", async () => {
	const onClose = vi.fn();
	render(
		<FilesInspector
			title="Documents"
			path="documents/"
			isFile={false}
			inline={false}
			onClose={onClose}
		>
			<p>Access information</p>
		</FilesInspector>,
	);
	await userEvent.click(
		screen.getByRole("button", { name: "Close file details" }),
	);
	expect(onClose).toHaveBeenCalledOnce();
	expect(
		screen.getByRole("region", { name: "File details" }),
	).toHaveTextContent("Access information");
});

it("keeps pending policy changes from being dismissed", async () => {
	const user = userEvent.setup();
	const onClose = vi.fn();
	render(
		<FilesInspector
			title="Policy"
			path="gallery/"
			isFile={false}
			inline
			busy
			onClose={onClose}
		>
			<button>Save in progress</button>
		</FilesInspector>,
	);
	expect(
		screen.getByRole("button", { name: "Close file details" }),
	).toBeDisabled();
	await user.click(screen.getByRole("button", { name: "Save in progress" }));
	await user.keyboard("{Escape}");
	expect(onClose).not.toHaveBeenCalled();
});
