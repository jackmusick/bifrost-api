import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { HmacSecretDeleteDialog } from "./HmacSecretDeleteDialog";

it("does not close on confirmation, guards pending dismissal and offers retry", async () => {
	const user = userEvent.setup();
	const props = { name: "Production integration", pending: false, error: false, onClose: vi.fn(), onConfirm: vi.fn() };
	const { rerender } = render(<HmacSecretDeleteDialog {...props} />);
	await user.click(screen.getByRole("button", { name: "Delete" }));
	expect(props.onConfirm).toHaveBeenCalledOnce();
	expect(props.onClose).not.toHaveBeenCalled();
	rerender(<HmacSecretDeleteDialog {...props} pending />);
	expect(screen.getByRole("button", { name: "Deleting…" })).toBeDisabled();
	expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
	await user.keyboard("{Escape}");
	expect(props.onClose).not.toHaveBeenCalled();
	rerender(<HmacSecretDeleteDialog {...props} error />);
	expect(screen.getByRole("alert")).toHaveTextContent("Could not delete");
	await user.click(screen.getByRole("button", { name: "Retry deletion" }));
	expect(props.onConfirm).toHaveBeenCalledTimes(2);
});
