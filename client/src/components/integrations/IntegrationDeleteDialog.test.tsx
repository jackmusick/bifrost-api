import { useState } from "react";
import { act, screen, renderWithProviders } from "@/test-utils";
import { expect, it, vi } from "vitest";
import { IntegrationDeleteDialog } from "./IntegrationDeleteDialog";

it("guards dismissal while pending, retains a failed deletion and closes after retry", async () => {
	let reject!: (error: Error) => void;
	const onConfirm = vi
		.fn()
		.mockImplementationOnce(
			() =>
				new Promise<void>((_resolve, fail) => {
					reject = fail;
				}),
		)
		.mockResolvedValueOnce(undefined);
	function Harness() {
		const [open, setOpen] = useState(true);
		return (
			<IntegrationDeleteDialog
				open={open}
				onOpenChange={setOpen}
				title="Delete Mapping"
				onConfirm={onConfirm}
			>
				Delete the selected mapping?
			</IntegrationDeleteDialog>
		);
	}
	const { user } = renderWithProviders(<Harness />);
	await user.click(screen.getByRole("button", { name: "Delete" }));
	expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
	await user.keyboard("{Escape}");
	expect(screen.getByRole("alertdialog")).toBeVisible();
	await act(async () => reject(new Error("Request failed")));
	expect(screen.getByRole("alert")).toHaveTextContent(
		"Could not delete. Try again.",
	);
	await user.click(screen.getByRole("button", { name: "Delete" }));
	expect(onConfirm).toHaveBeenCalledTimes(2);
	expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
});
