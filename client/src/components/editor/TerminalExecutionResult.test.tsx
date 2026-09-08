import { it, expect, vi, beforeEach } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { TerminalExecutionResult } from "./TerminalExecutionResult";
const { query } = vi.hoisted(() => ({ query: vi.fn() }));
vi.mock("@/hooks/useExecutions", () => ({ useExecutionResult: query }));
vi.mock("./TerminalResultModal", () => ({ TerminalResultModal: ({ open, html }: { open: boolean; html: string }) => open ? <div role="dialog">{html}</div> : null }));
beforeEach(() => query.mockReset());
it.each([0, false, "", "plain text"])("retains valid primitive result %s", value => {
	query.mockReturnValue({ data: { result: value, result_type: "text" } });
	renderWithProviders(<TerminalExecutionResult executionId="run" status="Success" />);
	expect(screen.getByRole("region", { name: "Execution result preview" }).textContent).toBe(String(value));
});
it("uses the API result_type to open HTML output", async () => {
	query.mockReturnValue({ data: { result: "<p>Report</p>", result_type: "html" } });
	const { user } = renderWithProviders(<TerminalExecutionResult executionId="run" status="Success" />);
	await user.click(screen.getByRole("button", { name: "View HTML result" }));
	expect(screen.getByRole("dialog")).toHaveTextContent("<p>Report</p>");
});
it("offers retry on a result lookup failure", async () => {
	const refetch = vi.fn();
	query.mockReturnValue({ isError: true, refetch });
	const { user } = renderWithProviders(<TerminalExecutionResult executionId="run" status="Success" />);
	await user.click(screen.getByRole("button", { name: "Retry result" }));
	expect(refetch).toHaveBeenCalledOnce();
});
it("does not show or request a result before completion", () => {
	query.mockReturnValue({});
	const { container } = renderWithProviders(<TerminalExecutionResult executionId="run" status="Running" />);
	expect(query).toHaveBeenCalledWith("run", false);
	expect(container).toBeEmptyDOMElement();
});
