import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen, waitFor } from "@/test-utils";
import { AgentDeleteDialog } from "./AgentDeleteDialog";
const remove = vi.hoisted(() => vi.fn());
vi.mock("@/hooks/useAgents", () => ({
	useDeleteAgent: () => ({ mutateAsync: remove, isPending: false }),
}));
describe("AgentDeleteDialog", () => {
	it("keeps a failed deletion open and retries before navigating", async () => {
		remove
			.mockRejectedValueOnce(new Error("offline"))
			.mockResolvedValueOnce(undefined);
		const onDeleted = vi.fn(),
			onOpenChange = vi.fn();
		const { user } = renderWithProviders(
			<AgentDeleteDialog
				agentId="agent-one"
				name="Customer operations"
				open
				onOpenChange={onOpenChange}
				onDeleted={onDeleted}
			/>,
		);
		await user.click(screen.getByRole("button", { name: "Delete" }));
		expect(await screen.findByRole("alert")).toHaveTextContent(
			"Could not delete the agent",
		);
		expect(onDeleted).not.toHaveBeenCalled();
		expect(onOpenChange).not.toHaveBeenCalled();
		await user.click(screen.getByRole("button", { name: "Retry delete" }));
		await waitFor(() => expect(onDeleted).toHaveBeenCalledOnce());
		expect(remove).toHaveBeenLastCalledWith({
			params: { path: { agent_id: "agent-one" } },
		});
		expect(onOpenChange).toHaveBeenCalledWith(false);
	});
});
