import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import type { HomeResource } from "@/services/home";
import { HomeBrowse } from "./HomeBrowse";

function makeResources(count: number): HomeResource[] {
	return Array.from({ length: count }, (_, index) => {
		const number = index + 1;
		return {
			key: `app:resource-${number}`,
			id: `app-${number}`,
			kind: "app",
			name: `Resource ${number}`,
			description: `Resource ${number} description`,
			icon: "app-window",
			organization_id: null,
			organization_name: "Global",
			href: `/apps/resource-${number}`,
			pinned: false,
			last_opened_at: null,
		};
	});
}

function renderBrowse({
	resources,
	page,
	onPageChange,
}: {
	resources: HomeResource[];
	page: number;
	onPageChange: (offset: number) => void;
}) {
	return (
		<HomeBrowse
			total={resources.length}
			grid={false}
			sort="name"
			visible={resources.slice(page * 12, page * 12 + 12)}
			resourceCount={resources.length}
			busy={false}
			page={page}
			onEdit={vi.fn()}
			updateParam={vi.fn()}
			onOpen={vi.fn()}
			onPin={vi.fn()}
			onPageChange={onPageChange}
		/>
	);
}

describe("HomeBrowse", () => {
	it("binds shared pagination offsets to the parent-supplied resource page", async () => {
		const resources = makeResources(13);
		const onPageChange = vi.fn();
		const { rerender, user } = renderWithProviders(
			renderBrowse({ resources, page: 0, onPageChange }),
		);

		expect(screen.getByText("Resource 1")).toBeVisible();
		expect(screen.getByText("Resource 12")).toBeVisible();
		expect(screen.queryByText("Resource 13")).not.toBeInTheDocument();

		await user.click(screen.getByRole("button", { name: "Next" }));
		expect(onPageChange).toHaveBeenCalledWith(12);

		rerender(renderBrowse({ resources, page: 1, onPageChange }));

		expect(screen.queryByText("Resource 1")).not.toBeInTheDocument();
		expect(screen.getByText("Resource 13")).toBeVisible();
		expect(
			screen.getByText("13–13 of 13 · Page 2 of 2"),
		).toBeVisible();

		await user.click(screen.getByRole("button", { name: "Previous" }));
		expect(onPageChange).toHaveBeenLastCalledWith(0);
	});
});
