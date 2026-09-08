import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { PaginationNext, PaginationLink } from "./pagination";
describe("Pagination interaction semantics", () => {
	it("supports keyboard activation for callback-only actions", async () => {
		const user = userEvent.setup();
		const click = vi.fn();
		render(<PaginationNext onClick={click} />);
		await user.tab();
		expect(screen.getByRole("button")).toHaveFocus();
		await user.keyboard("{Enter} ");
		expect(click).toHaveBeenCalledTimes(2);
	});
	it("keeps links and blocks disabled activation", async () => {
		const user = userEvent.setup();
		const click = vi.fn();
		render(
			<>
				<PaginationLink href="/page/2" isActive>
					2
				</PaginationLink>
				<PaginationNext
					href="/page/3"
					aria-disabled="true"
					onClick={click}
				/>
			</>,
		);
		expect(screen.getByRole("link", { name: "2" })).toHaveAttribute(
			"aria-current",
			"page",
		);
		const disabled = screen.getByRole("link", { name: "Go to next page" });
		expect(disabled).toHaveAttribute("tabindex", "-1");
		await user.click(disabled);
		expect(click).not.toHaveBeenCalled();
	});
});
