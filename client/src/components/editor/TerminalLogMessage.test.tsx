import { it, expect, vi, beforeEach } from "vitest";
import { fireEvent, renderWithProviders, screen } from "@/test-utils";
import { TerminalLogMessage } from "./TerminalLogMessage";
const { minimize, navigate } = vi.hoisted(() => ({ minimize: vi.fn(), navigate: vi.fn() }));
vi.mock("@/stores/editorStore", () => ({ useEditorStore: (select: (state: { minimizeEditor: typeof minimize }) => unknown) => select({ minimizeEditor: minimize }) }));
vi.mock("react-router-dom", async original => ({ ...await original<typeof import("react-router-dom")>(), useNavigate: () => navigate }));
beforeEach(() => vi.clearAllMocks());
it("routes internal links and minimizes the editor", async () => {
	const { user } = renderWithProviders(<TerminalLogMessage message="See [execution](/history/run?view=logs#last)" />);
	await user.click(screen.getByRole("link", { name: "execution" }));
	expect(navigate).toHaveBeenCalledWith("/history/run?view=logs#last");
	expect(minimize).toHaveBeenCalledOnce();
});
it("leaves modified clicks to the browser", () => {
	renderWithProviders(<TerminalLogMessage message="[execution](/history/run)" />);
	fireEvent.click(screen.getByRole("link"), { ctrlKey: true });
	expect(navigate).not.toHaveBeenCalled();
	expect(minimize).not.toHaveBeenCalled();
});
it("opens external pages separately with an accessible hint", () => {
	renderWithProviders(<TerminalLogMessage message="[documentation](https://example.test/docs)" />);
	const link = screen.getByRole("link", { name: "documentation (opens in a new tab)" });
	expect(link).toHaveAttribute("target", "_blank");
	expect(link).toHaveAttribute("rel", "noopener noreferrer");
});
it.each(["javascript:alert", "data:text/html,bad", "invalid://example"])("renders unsupported %s targets as text", target => {
	renderWithProviders(<TerminalLogMessage message={`[label](${target})`} />);
	expect(screen.queryByRole("link")).not.toBeInTheDocument();
	expect(screen.getByText("label")).toBeVisible();
});
