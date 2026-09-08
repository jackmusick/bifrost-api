import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { EntityCollectionStatus } from "./EntityCollectionStatus";

it("distinguishes missing and cached failures, retries the named source and removes recovered notices", async () => {
	const user = userEvent.setup();
	const forms = { name: "Forms", isLoading: false, isFetching: false, isError: true, hasData: false, onRetry: vi.fn() };
	const workflows = { ...forms, name: "Workflows", hasData: true, onRetry: vi.fn() };
	const { rerender } = render(<EntityCollectionStatus collections={[forms, workflows]} />);
	expect(screen.getAllByRole("alert")[0]).toHaveTextContent("This part of the page is incomplete");
	expect(screen.getAllByRole("alert")[1]).toHaveTextContent("Showing the last available data");
	await user.click(screen.getByRole("button", { name: "Retry forms" }));
	expect(forms.onRetry).toHaveBeenCalledOnce();
	expect(workflows.onRetry).not.toHaveBeenCalled();
	rerender(<EntityCollectionStatus collections={[{ ...forms, isFetching: true }, { ...workflows, isError: false, isFetching: true }]} />);
	expect(screen.getByRole("button", { name: "Retry forms" })).toBeDisabled();
	expect(screen.getByRole("status")).toHaveTextContent("Refreshing workflows");
	rerender(<EntityCollectionStatus collections={[{ ...forms, isError: false, hasData: true }]} />);
	expect(screen.queryByRole("region")).not.toBeInTheDocument();
});
