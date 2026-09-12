import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import type { HomeResource } from "@/services/home";
import { ResourceCard } from "./ResourceCard";

const app: HomeResource = {
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
};

describe("ResourceCard", () => {
	it("opens a resource and pins it without launching it", async () => {
		const onOpen = vi.fn();
		const onPin = vi.fn();
		const { user } = renderWithProviders(
			<ResourceCard resource={app} onOpen={onOpen} onPin={onPin} />,
		);

		await user.click(
			screen.getByRole("button", { name: "Dispatch Board" }),
		);
		await user.click(
			screen.getByRole("button", { name: "Pin Dispatch Board" }),
		);

		expect(onOpen).toHaveBeenCalledTimes(1);
		expect(onOpen).toHaveBeenCalledWith(app);
		expect(onPin).toHaveBeenCalledWith(app);
	});

	it("identifies the resource type", () => {
		renderWithProviders(
			<ResourceCard
				resource={{ ...app, kind: "form", name: "Intake" }}
				onOpen={vi.fn()}
				onPin={vi.fn()}
			/>,
		);
		expect(screen.getByText("Form")).toBeInTheDocument();
	});
});
