import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { CommitHistorySection } from "./CommitHistorySection";
const commits = [
	{
		sha: "0123456789abcdef",
		message:
			"Preserve complete commit messages\nIncluding their second line",
		author: "Design reviewer",
		timestamp: "2026-09-06T13:00:00Z",
		is_pushed: false,
	},
];
it("exposes local status and complete messages behind a keyboard disclosure", async () => {
	const user = userEvent.setup();
	render(
		<CommitHistorySection
			commits={commits}
			totalCommits={30}
			hasMore
			onRetry={vi.fn()}
		/>,
	);
	expect(screen.getByText("Local commit")).toBeVisible();
	expect(screen.getByText(/Including their second line/)).toBeVisible();
	expect(screen.getByText("0123456")).toBeVisible();
	expect(
		screen.getByText("Showing the latest 1 of 30 commits."),
	).toBeVisible();
	const disclosure = screen.getByRole("button", { name: "Commits 30" });
	disclosure.focus();
	await user.keyboard("{Enter}");
	expect(disclosure).toHaveAttribute("aria-expanded", "false");
	expect(screen.getByText("Local commit")).not.toBeVisible();
});
it("keeps known commits on failure and offers retry instead of showing an empty state", async () => {
	const user = userEvent.setup();
	const onRetry = vi.fn();
	render(
		<CommitHistorySection commits={commits} hasError onRetry={onRetry} />,
	);
	expect(screen.getByRole("alert")).toHaveTextContent(
		"Couldn’t load commit history",
	);
	expect(screen.getByText("Local commit")).toBeVisible();
	await user.click(
		screen.getByRole("button", { name: "Retry loading commits" }),
	);
	expect(onRetry).toHaveBeenCalledTimes(1);
	expect(screen.queryByText("No commits yet.")).not.toBeInTheDocument();
});
