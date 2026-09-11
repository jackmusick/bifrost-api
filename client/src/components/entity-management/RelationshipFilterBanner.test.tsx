import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { RelationshipFilterBanner } from "./RelationshipFilterBanner";

it("offers recovery and distinguishes unavailable relationships from cached results", async () => {
	const user = userEvent.setup();
	const props = { entityName: "Invoice processing", isError: true, isFetching: false, hasData: false, onRetry: vi.fn(), onClear: vi.fn() };
	const { rerender } = render(<RelationshipFilterBanner {...props} />);
	expect(screen.getByRole("alert")).toHaveTextContent("Could not load relationships");
	await user.click(screen.getByRole("button", { name: "Retry relationships" }));
	expect(props.onRetry).toHaveBeenCalledOnce();
	rerender(<RelationshipFilterBanner {...props} isFetching />);
	expect(screen.getByRole("button", { name: "Retrying…" })).toBeDisabled();
	expect(screen.getByRole("status")).toHaveTextContent("Retrying relationships");
	rerender(<RelationshipFilterBanner {...props} hasData />);
	expect(screen.getByRole("alert")).toHaveTextContent("Showing the last available results");
	await user.click(screen.getByRole("button", { name: "Clear filter" }));
	expect(props.onClear).toHaveBeenCalledOnce();
});
