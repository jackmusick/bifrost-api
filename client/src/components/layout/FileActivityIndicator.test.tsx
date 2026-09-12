import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { useFileActivityStore } from "@/stores/fileActivityStore";
import { FileActivityIndicator } from "./FileActivityIndicator";
vi.mock("@/contexts/AuthContext", () => ({
	useAuth: () => ({ user: { id: "self" } }),
}));
const event = {
	type: "file_push" as const,
	user_id: "other",
	user_name: "Alex",
	prefix: "workflows/example",
	timestamp: new Date().toISOString(),
	file_count: 3,
	is_watch: false,
};
beforeEach(() =>
	useFileActivityStore.setState({ recentPushes: [], activeWatchers: [] }),
);
describe("FileActivityIndicator", () => {
	it("omits own and expired pushes", () => {
		useFileActivityStore.setState({
			recentPushes: [
				{ ...event, user_id: "self" },
				{
					...event,
					timestamp: new Date(Date.now() - 120000).toISOString(),
				},
			],
		});
		renderWithProviders(<FileActivityIndicator />);
		expect(screen.queryByRole("button")).not.toBeInTheDocument();
	});
	it("opens activity details with the keyboard and returns focus on Escape", async () => {
		useFileActivityStore.setState({
			recentPushes: [event],
			activeWatchers: [{ ...event, type: "watch_start", is_watch: true }],
		});
		const { user } = renderWithProviders(<FileActivityIndicator />);
		const trigger = screen.getByRole("button", { name: /File activity:/ });
		trigger.focus();
		await user.keyboard("{Enter}");
		expect(
			screen.getByRole("dialog", { name: "File activity" }),
		).toBeVisible();
		expect(screen.getByText("Active watchers:")).toBeVisible();
		expect(screen.getByText("Recent file changes:")).toBeVisible();
		expect(screen.getAllByText("workflows/example")).toHaveLength(2);
		await user.keyboard("{Escape}");
		expect(trigger).toHaveFocus();
	});
});
