import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { SourceControlSetupState } from "./SourceControlSetupState";

it("offers retry after failure and prevents duplicate retries while pending", async () => {
	const user = userEvent.setup();
	const onAction = vi.fn();
	const { rerender } = render(
		<SourceControlSetupState state="error" onAction={onAction} />,
	);
	expect(screen.getByRole("alert")).toHaveTextContent(
		"Couldn’t load Git status.",
	);
	await user.click(screen.getByRole("button", { name: "Retry Git status" }));
	expect(onAction).toHaveBeenCalledTimes(1);
	rerender(
		<SourceControlSetupState state="error" busy onAction={onAction} />,
	);
	await user.click(screen.getByRole("button", { name: "Retrying…" }));
	expect(onAction).toHaveBeenCalledTimes(1);
	rerender(
		<SourceControlSetupState state="initialize" onAction={onAction} />,
	);
	expect(screen.queryByRole("alert")).not.toBeInTheDocument();
	await user.click(screen.getByRole("button", { name: "Fetch from GitHub" }));
	expect(onAction).toHaveBeenCalledTimes(2);
	rerender(
		<SourceControlSetupState state="initialize" busy onAction={onAction} />,
	);
	expect(screen.getByRole("button", { name: "Fetching…" })).toBeDisabled();
});
