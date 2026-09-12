import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { HmacSecretCreateForm } from "./HmacSecretCreateForm";

it("preserves controlled entries on error, submits on Enter and locks pending controls", async () => {
	const user = userEvent.setup();
	const props = { name: "Preview", secret: "synthetic-only", scheme: "shopify" as const, busy: false, creating: false, error: true, onName: vi.fn(), onSecret: vi.fn(), onScheme: vi.fn(), onSubmit: vi.fn(event => event.preventDefault()), onCancel: vi.fn() };
	const { rerender } = render(<HmacSecretCreateForm {...props} />);
	expect(screen.getByRole("alert")).toHaveTextContent("Your entries are still here");
	expect(screen.getByLabelText("Secret (optional)")).toHaveValue("synthetic-only");
	expect(screen.getByLabelText("Secret (optional)")).toHaveAttribute("type", "password");
	await user.keyboard("{Enter}");
	expect(props.onSubmit).toHaveBeenCalledOnce();
	rerender(<HmacSecretCreateForm {...props} busy creating error={false} />);
	expect(screen.getByLabelText("Name")).toBeDisabled();
	expect(screen.getByRole("combobox", { name: "HMAC scheme" })).toBeDisabled();
	expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
	expect(screen.getByRole("button", { name: "Creating..." })).toBeDisabled();
});
