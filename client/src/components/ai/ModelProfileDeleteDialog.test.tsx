import { expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { ModelProfileDeleteDialog } from "./ModelProfileDeleteDialog";
import type { AIModelProfile } from "@/services/aiModels";
const profile: AIModelProfile = { id: "synthetic", name: "Test profile", assignment_keys: [], connection_id: "connection", model: "test-model", enabled_for_chat: false, connection: { id: "connection", name: "Test provider", provider: "openai", endpoint: null }, referenced_agent_count: 0, created_at: "2026-09-06T00:00:00Z", updated_at: "2026-09-06T00:00:00Z" };
it("requires confirmation and retains the dialog during failure/pending", async () => {
	const onConfirm = vi.fn(), onClose = vi.fn();
	const { user, rerender } = renderWithProviders(<ModelProfileDeleteDialog profile={profile} pending={false} failed={false} onConfirm={onConfirm} onClose={onClose} />);
	await user.click(screen.getByRole("button", { name: "Delete profile" }));
	expect(onConfirm).toHaveBeenCalledOnce();
	expect(onClose).not.toHaveBeenCalled();
	rerender(<ModelProfileDeleteDialog profile={profile} pending failed={false} onConfirm={onConfirm} onClose={onClose} />);
	await user.keyboard("{Escape}");
	expect(onClose).not.toHaveBeenCalled();
	expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
	rerender(<ModelProfileDeleteDialog profile={profile} pending={false} failed onConfirm={onConfirm} onClose={onClose} />);
	expect(screen.getByRole("alert")).toHaveTextContent("Could not delete");
	expect(screen.getByRole("button", { name: "Delete profile" })).toBeEnabled();
});
it("explains known assignment dependencies before allowing deletion", () => {
	renderWithProviders(<ModelProfileDeleteDialog profile={{...profile, assignment_keys: ["primary"]}} pending={false} failed={false} onConfirm={vi.fn()} onClose={vi.fn()} />);
	expect(screen.getByText(/has active assignments/)).toBeVisible();
	expect(screen.getByRole("button", { name: "Delete profile" })).toBeDisabled();
});

it("explains known agent dependencies before allowing deletion", () => {
 renderWithProviders(<ModelProfileDeleteDialog profile={{...profile, referenced_agent_count: 2}} pending={false} failed={false} onConfirm={vi.fn()} onClose={vi.fn()} />);
 expect(screen.getByText(/used by 2 agents/)).toBeVisible();
 expect(screen.getByRole("button", { name: "Delete profile" })).toBeDisabled();
});
