import { expect, it, vi } from "vitest";
import { renderWithProviders, screen, within } from "@/test-utils";
import type { HomeResource } from "@/services/home";
import { HomeCatalogOverview } from "./HomeCatalogOverview";

it("limits the type-grouped preview and exposes both full category and full catalog actions", async () => {
	const resources = Array.from({ length: 4 }, (_, i) => ({
		key: `app:${i}`,
		id: String(i),
		kind: "app",
		name: `App ${i}`,
		href: `/apps/${i}`,
		organization_name: "Global",
		pinned: false,
	})) as HomeResource[];
	const onCategory = vi.fn();
	const onViewAll = vi.fn();
	const { user } = renderWithProviders(
		<HomeCatalogOverview
			resources={resources}
			onOpen={vi.fn()}
			onPin={vi.fn()}
			busy={false}
			onCategory={onCategory}
			onViewAll={onViewAll}
		/>,
	);
	const apps = within(screen.getByRole("region", { name: "Apps" }));
	expect(apps.getByRole("button", { name: "App 1" })).toBeInTheDocument();
	expect(
		apps.queryByRole("button", { name: "App 2" }),
	).not.toBeInTheDocument();
	await user.click(screen.getByRole("button", { name: "View all apps" }));
	expect(onCategory).toHaveBeenCalledWith("app");
	await user.click(screen.getByRole("button", { name: "Browse all 4" }));
	expect(onViewAll).toHaveBeenCalledOnce();
});
