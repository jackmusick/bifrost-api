import { it, expect, vi } from "vitest";
import { renderWithProviders, screen, waitFor } from "@/test-utils";
import { TextExecutionResult } from "./TextExecutionResult";
import { copyToClipboard } from "@/lib/clipboard";

vi.mock("@/lib/clipboard", () => ({ copyToClipboard: vi.fn() }));

it("copies exact text and offers recovery when copying fails", async () => {
	vi.mocked(copyToClipboard).mockResolvedValueOnce(false).mockResolvedValueOnce(true);
	const value = "first line\nsecond line";
	const { user } = renderWithProviders(<TextExecutionResult value={value} />);
	await user.click(screen.getByRole("button", { name: "Copy result" }));
	expect(screen.getByRole("alert")).toHaveTextContent("Could not copy");
	await user.click(screen.getByRole("button", { name: "Copy result" }));
	expect(copyToClipboard).toHaveBeenLastCalledWith(value);
	expect(screen.getByRole("status")).toHaveTextContent("Result copied");
	expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

it("keeps old copy feedback out of a newly displayed result", async () => {
	let finish!: (value: boolean) => void;
	vi.mocked(copyToClipboard).mockReturnValueOnce(new Promise(resolve => { finish = resolve; }));
	const { user, rerender } = renderWithProviders(<TextExecutionResult value="old result" />);
	await user.click(screen.getByRole("button", { name: "Copy result" }));
	rerender(<TextExecutionResult value="new result" />);
	finish(true);
	await waitFor(() => expect(screen.getByRole("button", { name: "Copy result" })).toBeEnabled());
	expect(screen.queryByText("Result copied")).not.toBeInTheDocument();
	expect(screen.getByRole("region", { name: "Text result" })).toHaveTextContent("new result");
});
