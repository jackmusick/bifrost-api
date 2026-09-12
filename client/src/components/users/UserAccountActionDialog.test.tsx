import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen, waitFor } from "@/test-utils";
import { UserAccountActionDialog } from "./UserAccountActionDialog";

describe("UserAccountActionDialog", () => {
	it.each(["disable", "delete"] as const)(
		"protects pending %s and keeps failures recoverable",
		async (mode) => {
			let reject!: (error: Error) => void;
			const onConfirm = vi
				.fn()
				.mockImplementationOnce(
					() =>
						new Promise<void>((_resolve, fail) => {
							reject = fail;
						}),
				)
				.mockResolvedValue(undefined);
			const onOpenChange = vi.fn();
			const { user } = renderWithProviders(
				<UserAccountActionDialog
					mode={mode}
					name="Alexandra Example"
					onConfirm={onConfirm}
					onOpenChange={onOpenChange}
				/>,
			);
			const action =
				mode === "delete" ? /^permanently delete$/i : /^disable$/i;
			await user.click(screen.getByRole("button", { name: action }));
			expect(
				screen.getByRole("button", { name: "Cancel" }),
			).toBeDisabled();
			await user.keyboard("{Escape}");
			expect(onOpenChange).not.toHaveBeenCalled();
			reject(new Error("Synthetic failure"));
			await waitFor(() =>
				expect(screen.getByRole("alert")).toHaveFocus(),
			);
			expect(screen.getByRole("alert")).toHaveTextContent(
				"Synthetic failure",
			);
			await user.click(screen.getByRole("button", { name: action }));
			expect(onConfirm).toHaveBeenCalledTimes(2);
			expect(screen.queryByRole("alert")).not.toBeInTheDocument();
		},
	);
});
