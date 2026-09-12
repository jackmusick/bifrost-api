import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mutateAsync = vi.fn().mockResolvedValue({ default_system_prompt: "Be direct." });
const refetch = vi.fn().mockResolvedValue(undefined);
let behaviorData = { default_system_prompt: "Be helpful." };

vi.mock("@/lib/api-client", () => ({
	$api: {
		useQuery: () => ({
			data: behaviorData,
			isLoading: false,
			refetch,
		}),
		useMutation: () => ({ mutateAsync, isPending: false }),
	},
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

import { AIBehaviorSettings } from "./AIBehaviorSettings";

beforeEach(() => { behaviorData = { default_system_prompt: "Be helpful." }; mutateAsync.mockReset().mockResolvedValue({ default_system_prompt: "Be direct." }); });

describe("AIBehaviorSettings", () => {
	it("saves agentless Chat instructions", async () => {
		const user = userEvent.setup();
		render(<AIBehaviorSettings />);

		const instructions = screen.getByLabelText("Instructions");
		await user.clear(instructions);
		await user.type(instructions, "Be direct.");
		await user.click(screen.getByRole("button", { name: "Save instructions" }));

		await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith({
			body: { default_system_prompt: "Be direct." },
		}));
	});
});


it("keeps unsaved edits when background data changes", async () => {
	const user = userEvent.setup();
	const { rerender } = render(<AIBehaviorSettings />);
	const input = screen.getByLabelText("Instructions");
	await user.clear(input);
	await user.type(input, "Keep my draft");
	behaviorData = { default_system_prompt: "Background update" };
	rerender(<AIBehaviorSettings />);
	expect(input).toHaveValue("Keep my draft");
});

it("retains a failed save and lets the user retry", async () => {
	mutateAsync.mockRejectedValueOnce(new Error("Synthetic failure"));
	const user = userEvent.setup();
	render(<AIBehaviorSettings />);
	await user.clear(screen.getByLabelText("Instructions"));
	await user.type(screen.getByLabelText("Instructions"), "Retry this draft");
	await user.click(screen.getByRole("button", { name: "Save instructions" }));
	expect(await screen.findByRole("alert")).toHaveTextContent("Your draft is preserved");
	expect(screen.getByLabelText("Instructions")).toHaveValue("Retry this draft");
	await user.click(screen.getByRole("button", { name: "Save instructions" }));
	await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
});
