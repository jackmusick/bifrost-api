import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { HmacSecretList, type HmacSecretSummary } from "./HmacSecretList";

it("keeps failures distinct from empty data and retains records during refresh", async () => {
	const user = userEvent.setup();
	const props = { loading: false, error: true, onRetry: vi.fn(), onToggle: vi.fn(), onDelete: vi.fn() };
	const secret: HmacSecretSummary = { id: "one", name: "Production integration", is_active: true, hmac_scheme: "shopify", created_at: "2026-09-01" };
	const { rerender } = render(<HmacSecretList {...props} secrets={[]} />);
	expect(screen.queryByText("No embed secrets configured.")).not.toBeInTheDocument();
	await user.click(screen.getByRole("button", { name: "Retry embed secrets" }));
	expect(props.onRetry).toHaveBeenCalledOnce();
	rerender(<HmacSecretList {...props} secrets={[secret]} loading />);
	expect(screen.getByRole("heading", { name: secret.name })).toBeInTheDocument();
	expect(screen.getByRole("button", { name: "Deactivate" })).toBeDisabled();
	expect(screen.getByRole("status")).toHaveTextContent("Refreshing embed secrets");
	rerender(<HmacSecretList {...props} secrets={[secret]} error={false} />);
	await user.click(screen.getByRole("button", { name: "Deactivate" }));
	await user.click(
		screen.getByRole("button", { name: `More actions for ${secret.name}` }),
	);
	await user.click(
		screen.getByRole("menuitem", {
			name: `Delete ${secret.name}`,
		}),
	);
	expect(props.onToggle).toHaveBeenCalledWith(secret);
	expect(props.onDelete).toHaveBeenCalledWith(secret);
});
