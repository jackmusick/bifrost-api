import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
const { copy } = vi.hoisted(() => ({ copy: vi.fn() }));
vi.mock("@/lib/clipboard", () => ({ copyToClipboard: copy }));
import { HmacSecretReveal } from "./HmacSecretReveal";

it("retains the value after copy failure and confirms only successful copying", async () => {
	const user = userEvent.setup();
	const onDismiss = vi.fn();
	let finish!: (success: boolean) => void;
	copy.mockImplementationOnce(() => new Promise<boolean>(resolve => { finish = resolve; })).mockResolvedValueOnce(true);
	render(<HmacSecretReveal value="synthetic-test-value" onDismiss={onDismiss} />);
	await user.tab();
	expect(window.getSelection()?.toString()).toBe("synthetic-test-value");
	await user.click(screen.getByRole("button", { name: "Copy secret" }));
	expect(screen.getByRole("button", { name: "Copying…" })).toBeDisabled();
	expect(screen.getByRole("button", { name: "Dismiss secret" })).toBeDisabled();
	finish(false);
	expect(await screen.findByRole("alert")).toHaveTextContent("Could not copy the secret");
	expect(screen.getByLabelText("Secret value")).toHaveTextContent("synthetic-test-value");
	expect(screen.queryByRole("status")).not.toBeInTheDocument();
	await user.click(screen.getByRole("button", { name: "Copy secret" }));
	await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Secret copied"));
	await user.click(screen.getByRole("button", { name: "Dismiss secret" }));
	expect(onDismiss).toHaveBeenCalledOnce();
});

it("recovers if the clipboard helper throws", async () => {
	const user = userEvent.setup();
	copy.mockRejectedValueOnce(new Error("Clipboard unavailable"));
	render(<HmacSecretReveal value="synthetic-test-value" onDismiss={() => {}} />);
	await user.click(screen.getByRole("button", { name: "Copy secret" }));
	expect(await screen.findByRole("alert")).toHaveTextContent("Could not copy");
	expect(screen.getByRole("button", { name: "Copy secret" })).toBeEnabled();
});
