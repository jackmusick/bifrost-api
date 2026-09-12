import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { useScopeStore } from "@/stores/scopeStore";
import { RegisterWorkflowDialog } from "./RegisterWorkflowDialog";

vi.mock("@/components/forms/OrganizationSelect", () => ({
	OrganizationSelect: ({ value }: { value: string | null }) => (
		<div>{value ?? "Global"}</div>
	),
}));

it("starts each registration from the current organization scope", async () => {
	useScopeStore
		.getState()
		.setScope({ type: "global", orgId: null, orgName: null });
	const user = userEvent.setup();
	const onConfirm = vi.fn();
	const props = { functionName: "workflow", onConfirm, onCancel: vi.fn() };
	const { rerender } = render(<RegisterWorkflowDialog {...props} open />);
	await user.click(
		screen.getByRole("button", { name: "Register" }),
	);
	expect(onConfirm).toHaveBeenLastCalledWith(null);
	rerender(<RegisterWorkflowDialog {...props} open={false} />);
	act(() =>
		useScopeStore
			.getState()
			.setScope({
				type: "organization",
				orgId: "new-org",
				orgName: "New organization",
			}),
	);
	rerender(<RegisterWorkflowDialog {...props} open />);
	await user.click(
		screen.getByRole("button", { name: "Register" }),
	);
	expect(onConfirm).toHaveBeenLastCalledWith("new-org");
	act(() =>
		useScopeStore
			.getState()
			.setScope({ type: "global", orgId: null, orgName: null }),
	);
});
