import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";

import { renderWithProviders } from "@/test-utils";
import { GitHubCreateRepositoryDialog } from "./GitHubCreateRepositoryDialog";

beforeEach(() => {
	vi.restoreAllMocks();
	Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
		value: vi.fn(),
		configurable: true,
	});
});

describe("GitHubCreateRepositoryDialog", () => {
	it("focuses the inline failure and keeps the footer visible in a bounded dialog", async () => {
		const onClose = vi.fn();
		const onConfirm = vi.fn();

		renderWithProviders(
			<GitHubCreateRepositoryDialog
				open
				name="repo-name"
				description="repo description"
				isPrivate
				pending={false}
				failed
				onClose={onClose}
				onConfirm={onConfirm}
				onNameChange={vi.fn()}
				onDescriptionChange={vi.fn()}
				onPrivateChange={vi.fn()}
			/>,
		);

		const alert = await screen.findByRole("alert");
		await waitFor(() => expect(alert).toHaveFocus());
		expect(alert).toHaveTextContent(/could not create repository/i);
		expect(
			screen.getByRole("button", { name: /^cancel$/i }),
		).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: /create repository/i }),
		).toBeInTheDocument();
	});
});
