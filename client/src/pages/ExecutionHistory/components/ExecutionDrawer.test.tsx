import { expect, it, vi } from "vitest";
import { renderWithProviders, screen, waitFor } from "@/test-utils";
import { ExecutionDrawer } from "./ExecutionDrawer";
const copy = vi.hoisted(() => vi.fn());
vi.mock("@/lib/clipboard", () => ({copyToClipboard: (text: string) => copy(text)}));
vi.mock("@/pages/ExecutionDetails", () => ({ExecutionDetails: () => <p>Execution content</p>}));

it("reports copy failure accurately and retries without closing the drawer", async () => {
    copy.mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    const onOpenChange = vi.fn();
    const {user} = renderWithProviders(<ExecutionDrawer executionId="run-one" open onOpenChange={onOpenChange} />);
    await user.click(screen.getByRole("button", {name: "Copy execution ID"}));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Couldn't copy"));
    await user.click(screen.getByRole("button", {name: "Copy execution ID"}));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Execution ID copied"));
    expect(copy).toHaveBeenLastCalledWith("run-one");
    expect(onOpenChange).not.toHaveBeenCalled();
    expect(screen.getByRole("link", {name: "Open execution in new tab"})).toHaveAttribute("href", "/history/run-one");
    await user.click(screen.getByRole("button", {name: "Close execution details"}));
    expect(onOpenChange).toHaveBeenCalledWith(false);
});
