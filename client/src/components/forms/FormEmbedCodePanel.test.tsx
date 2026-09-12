import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
const { copy } = vi.hoisted(() => ({ copy: vi.fn() }));
vi.mock("@/lib/clipboard", () => ({ copyToClipboard: copy }));
import { FormEmbedCodePanel } from "./FormEmbedCodePanel";

it("retains selectable code after failed copy and clears confirmation when the snippet changes", async () => {
	const user = userEvent.setup();
	const code = '<iframe src="/synthetic-only"></iframe>';
	copy.mockResolvedValueOnce(false).mockResolvedValueOnce(true);
	const { rerender } = render(<FormEmbedCodePanel code={code} />);
	await user.click(screen.getByRole("button", { name: "Copy embed code" }));
	expect(await screen.findByRole("alert")).toHaveTextContent("copy manually");
	await user.tab();
	expect(window.getSelection()?.toString()).toBe(code);
	await user.click(screen.getByRole("button", { name: "Copy embed code" }));
	expect(await screen.findByRole("status")).toHaveTextContent("Embed code copied");
	expect(copy).toHaveBeenLastCalledWith(code);
	rerender(<FormEmbedCodePanel code="changed snippet" />);
	expect(screen.queryByRole("status")).not.toBeInTheDocument();
});

it("does not announce an old snippet as copied after options change while copying", async () => {
	const user = userEvent.setup();
	let resolve!: (result: boolean) => void;
	copy.mockImplementationOnce(() => new Promise<boolean>(done => { resolve = done; }));
	const { rerender } = render(<FormEmbedCodePanel code="old snippet" />);
	await user.click(screen.getByRole("button", { name: "Copy embed code" }));
	expect(screen.getByRole("button", { name: "Copy embed code" })).toBeDisabled();
	rerender(<FormEmbedCodePanel code="new snippet" />);
	resolve(true);
	await waitFor(() => expect(screen.getByRole("button", { name: "Copy embed code" })).toBeEnabled());
	expect(screen.queryByRole("status")).not.toBeInTheDocument();
});
