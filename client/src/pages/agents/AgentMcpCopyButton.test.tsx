import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { renderWithProviders, screen, waitFor } from "@/test-utils";
import { RecordActionsMenu } from "@/components/common/RecordActionsMenu";
import { AgentMcpCopyButton } from "./AgentMcpCopyButton";

const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();

vi.mock("sonner", () => ({
	toast: {
		success: (...args: unknown[]) => mockToastSuccess(...args),
		error: (...args: unknown[]) => mockToastError(...args),
	},
}));

describe("AgentMcpCopyButton", () => {
	beforeEach(() => {
		mockToastSuccess.mockClear();
		mockToastError.mockClear();
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	it("copies the agent MCP URL from the default button", async () => {
		const { user } = renderWithProviders(
			<AgentMcpCopyButton agentId="agent-1" />,
		);
		const writeText = vi
			.spyOn(navigator.clipboard, "writeText")
			.mockResolvedValue(undefined);

		await user.click(
			screen.getByRole("button", { name: "Copy agent MCP URL" }),
		);

		await waitFor(() =>
			expect(writeText).toHaveBeenCalledWith(
				`${window.location.origin}/mcp/agent-1`,
			),
		);
		await waitFor(() =>
			expect(mockToastSuccess).toHaveBeenCalledWith(
				"Agent MCP URL copied",
			),
		);
	});

	it("copies the agent MCP URL from a menu item", async () => {
		const { user } = renderWithProviders(
			<RecordActionsMenu label="Alpha actions">
				<AgentMcpCopyButton agentId="agent-2" variant="menuitem" />
			</RecordActionsMenu>,
		);
		const writeText = vi
			.spyOn(navigator.clipboard, "writeText")
			.mockResolvedValue(undefined);

		await user.click(screen.getByRole("button", { name: "Alpha actions" }));
		await user.click(
			screen.getByRole("menuitem", { name: "Copy MCP URL" }),
		);

		await waitFor(() =>
			expect(writeText).toHaveBeenCalledWith(
				`${window.location.origin}/mcp/agent-2`,
			),
		);
	});

	it("shows an error toast when clipboard write fails", async () => {
		const { user } = renderWithProviders(
			<AgentMcpCopyButton agentId="agent-3" />,
		);
		vi.spyOn(navigator.clipboard, "writeText").mockRejectedValueOnce(
			new Error("denied"),
		);

		await user.click(
			screen.getByRole("button", { name: "Copy agent MCP URL" }),
		);

		await waitFor(() =>
			expect(mockToastError).toHaveBeenCalledWith(
				"Could not copy the MCP URL. Check your browser clipboard permissions and try again.",
			),
		);
	});
});
