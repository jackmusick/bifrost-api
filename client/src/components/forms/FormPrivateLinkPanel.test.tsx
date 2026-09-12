import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { FormPrivateLinkPanel } from "./FormPrivateLinkPanel";

it("selects the private URL for copying and announces successful copy without changing access", async () => {
	const user = userEvent.setup();
	const onCopy = vi.fn();
	const url = "https://bifrost.example/execute/form";
	const { rerender } = render(<FormPrivateLinkPanel url={url} copied={false} onCopy={onCopy} />);
	const input = screen.getByRole("textbox", { name: "Private form link" }) as HTMLInputElement;
	await user.tab();
	expect(input).toHaveFocus();
	expect(input.selectionStart).toBe(0);
	expect(input.selectionEnd).toBe(url.length);
	await user.click(screen.getByRole("button", { name: "Copy private link" }));
	expect(onCopy).toHaveBeenCalledOnce();
	expect(screen.getByRole("link", { name: "Open private link" })).toHaveAttribute("href", url);
	rerender(<FormPrivateLinkPanel url={url} copied onCopy={onCopy} />);
	expect(screen.getByRole("status")).toHaveTextContent("Private link copied");
});
