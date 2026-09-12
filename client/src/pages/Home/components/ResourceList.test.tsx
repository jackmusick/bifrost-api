import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen, within } from "@/test-utils";
import type { HomeResource } from "@/services/home";
import { ResourceList } from "./ResourceList";

const resources: HomeResource[] = [
	{
		key: "app:dispatch",
		id: "app-1",
		kind: "app",
		name: "Dispatch Board",
		description: "Coordinate field work",
		icon: "app-window",
		organization_id: null,
		organization_name: "Global",
		href: "/apps/dispatch",
		pinned: false,
		last_opened_at: null,
	},
	{
		key: "agent:help",
		id: "agent-1",
		kind: "agent",
		name: "Helpdesk Agent",
		description: "Answer tickets",
		icon: "bot",
		organization_id: "org-1",
		organization_name: "Acme",
		href: "/agents/agent-1",
		pinned: true,
		last_opened_at: null,
	},
];

describe("ResourceList", () => {
	it("opens rows, exposes type actions, and toggles pinned state", async () => {
		const onOpen = vi.fn();
		const onPin = vi.fn();
		const { user } = renderWithProviders(
			<ResourceList
				resources={resources}
				onOpen={onOpen}
				onPin={onPin}
			/>,
		);

		const list = screen.getByRole("list", { name: "Resources" });
		await user.click(within(list).getByText("Helpdesk Agent").closest("button")!);
		await user.click(within(list).getByRole("button", { name: "Chat" }));
		await user.click(
			within(list).getByRole("button", { name: "Unpin Helpdesk Agent" }),
		);

		expect(onOpen).toHaveBeenCalledTimes(2);
		expect(onOpen).toHaveBeenCalledWith(resources[1]);
		expect(onPin).toHaveBeenCalledWith(resources[1]);
	});
});
