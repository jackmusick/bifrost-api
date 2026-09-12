import { expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { ProviderDeleteDialog } from "./ProviderDeleteDialog";
import type { AIProviderConnection } from "@/services/aiModels";
const provider = { id: "synthetic", name: "Test provider", profile_count: 0 } as AIProviderConnection;
it("requires confirmation and retains the dialog during failure/pending", async () => {
	const onConfirm = vi.fn(), onClose = vi.fn();
	const { user, rerender } = renderWithProviders(<ProviderDeleteDialog provider={provider} pending={false} failed={false} onConfirm={onConfirm} onClose={onClose} />);
	await user.click(screen.getByRole("button", { name: "Delete connection" }));
	expect(onConfirm).toHaveBeenCalledOnce();
	expect(onClose).not.toHaveBeenCalled();
	rerender(<ProviderDeleteDialog provider={provider} pending failed={false} onConfirm={onConfirm} onClose={onClose} />);
	await user.keyboard("{Escape}");
	expect(onClose).not.toHaveBeenCalled();
	expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
	rerender(<ProviderDeleteDialog provider={provider} pending={false} failed onConfirm={onConfirm} onClose={onClose} />);
	expect(screen.getByRole("alert")).toHaveTextContent("Could not delete");
	expect(screen.getByRole("button", { name: "Delete connection" })).toBeEnabled();
});
it("explains known profile dependencies before allowing deletion", () => {
	renderWithProviders(<ProviderDeleteDialog provider={{...provider, profile_count: 2}} pending={false} failed={false} onConfirm={vi.fn()} onClose={vi.fn()} />);
	expect(screen.getByText(/used by 2 profiles/)).toBeVisible();
	expect(screen.getByRole("button", { name: "Delete connection" })).toBeDisabled();
});
