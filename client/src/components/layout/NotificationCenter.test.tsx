import { beforeEach, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { NotificationCenter } from "./NotificationCenter";
import { useNotificationStore } from "@/stores/notificationStore";

const state = vi.hoisted(() => ({
	notifications: [],
	dismiss: vi.fn(),
	clearAll: vi.fn(),
	isLoading: false,
	error: null as Error | null,
	refetch: vi.fn(),
	isFetching: false,
}));
vi.mock("@/hooks/useNotifications", () => ({ useNotifications: () => state }));
beforeEach(() => {
	vi.clearAllMocks();
	state.isLoading = false;
	state.error = null;
	state.isFetching = false;
	useNotificationStore.setState({ notifications: [], alerts: [] });
});

it("distinguishes initial loading from an empty result", async () => {
	state.isLoading = true;
	const user = userEvent.setup();
	const view = render(
		<MemoryRouter>
			<NotificationCenter />
		</MemoryRouter>,
	);
	await user.click(screen.getByRole("button", { name: "Notifications" }));
	expect(screen.getByRole("status")).toHaveTextContent(
		"Loading notifications",
	);
	expect(screen.queryByText("No notifications")).not.toBeInTheDocument();
	state.isLoading = false;
	view.rerender(
		<MemoryRouter>
			<NotificationCenter />
		</MemoryRouter>,
	);
	expect(screen.getByText("No notifications")).toBeVisible();
});

it("retains local messages on fetch failure and offers guarded retry", async () => {
	state.error = new Error("Unavailable");
	useNotificationStore
		.getState()
		.addAlert({
			title: "Saved locally",
			body: "Your existing notification remains readable.",
			status: "info",
		});
	const user = userEvent.setup();
	const view = render(
		<MemoryRouter>
			<NotificationCenter />
		</MemoryRouter>,
	);
	await user.click(screen.getByRole("button", { name: "Notifications" }));
	expect(screen.getByRole("alert")).toHaveTextContent(
		"Couldn't load notifications",
	);
	expect(
		screen.getByRole("article", { name: "Saved locally" }),
	).toBeVisible();
	expect(screen.queryByText("No notifications")).not.toBeInTheDocument();
	await user.click(
		screen.getByRole("button", { name: "Retry" }),
	);
	expect(state.refetch).toHaveBeenCalledOnce();
	state.isFetching = true;
	view.rerender(
		<MemoryRouter>
			<NotificationCenter />
		</MemoryRouter>,
	);
	expect(screen.getByRole("button", { name: "Retrying…" })).toBeDisabled();
	await user.click(
		screen.getByRole("button", { name: "Dismiss Saved locally" }),
	);
	expect(
		screen.queryByRole("article", { name: "Saved locally" }),
	).not.toBeInTheDocument();
	expect(screen.queryByText("No notifications")).not.toBeInTheDocument();
});
