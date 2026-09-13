import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/detail-route-loaders", () => ({
	prefetchApplicationDetail: vi.fn(),
}));

vi.mock("@/components/solutions/SolutionManagedBadge", () => ({
	SolutionManagedBadge: () => <span>Solution managed</span>,
}));

import {
	ApplicationListSurface,
	type ApplicationListItem,
} from "./ApplicationListSurface";

function makeApp(
	overrides: Partial<ApplicationListItem> = {},
): ApplicationListItem {
	return {
		id: "11111111-1111-1111-1111-111111111111",
		name: "Dispatch Board",
		description: "Dispatch queue",
		icon: null,
		slug: "dispatch-board",
		organization_id: null,
		published_at: "2026-09-12T12:00:00Z",
		deployed_at: "2026-09-12T12:00:00Z",
		created_at: "2026-09-12T12:00:00Z",
		updated_at: "2026-09-12T12:00:00Z",
		created_by: null,
		is_published: true,
		has_unpublished_changes: false,
		access_level: "authenticated",
		app_model: "standalone_v2",
		is_solution_managed: false,
		solution_id: null,
		role_ids: [],
		repo_path: null,
		logo: null,
		logo_url: null,
		logo_version: null,
		sdk_package_version: "1.0.0",
		sdk_fingerprint: "old",
		sdk_contract_version: 1,
		sdk_built_at: "2026-09-12T12:00:00Z",
		sdk_status: "update_available",
		sdk_source_available: true,
		...overrides,
	};
}

function renderSurface(
	props: Partial<React.ComponentProps<typeof ApplicationListSurface>> = {},
) {
	return render(
		<ApplicationListSurface
			apps={[makeApp()]}
			viewMode="grid"
			isPlatformAdmin={false}
			canManageApps={true}
			getOrgName={() => "Global"}
			onLaunch={vi.fn()}
			onUpdateSdk={vi.fn()}
			{...props}
		/>,
	);
}

describe("ApplicationListSurface SDK update affordances", () => {
	it("shows SDK drift in the status cluster and queues updates from the overflow menu", async () => {
		const user = userEvent.setup();
		const onUpdateSdk = vi.fn();
		renderSurface({ onUpdateSdk });

		expect(screen.getByText("SDK update available")).toBeVisible();

		await user.click(
			screen.getByRole("button", { name: "Dispatch Board actions" }),
		);
		await user.click(
			screen.getByRole("menuitem", { name: /update sdk/i }),
		);

		expect(onUpdateSdk).toHaveBeenCalledWith(
			expect.objectContaining({ id: makeApp().id }),
		);
	});

	it("renders source-unavailable state without enabling SDK update", async () => {
		const user = userEvent.setup();
		const onUpdateSdk = vi.fn();
		renderSurface({
			apps: [
				makeApp({
					sdk_status: "update_required",
					sdk_source_available: false,
				}),
			],
			onUpdateSdk,
		});

		expect(screen.getByText("SDK update required")).toBeVisible();
		expect(screen.getByText("Source unavailable")).toBeVisible();

		await user.click(
			screen.getByRole("button", { name: "Dispatch Board actions" }),
		);

		expect(
			screen.getByRole("menuitem", { name: /source unavailable/i }),
		).toHaveAttribute("aria-disabled", "true");
		expect(onUpdateSdk).not.toHaveBeenCalled();
	});

	it("offers rebuild for unknown SDK status when source is available", async () => {
		const user = userEvent.setup();
		const onUpdateSdk = vi.fn();
		renderSurface({
			apps: [
				makeApp({
					sdk_status: "unknown",
					sdk_source_available: true,
				}),
			],
			onUpdateSdk,
		});

		expect(screen.getByText("SDK unknown")).toBeVisible();

		await user.click(
			screen.getByRole("button", { name: "Dispatch Board actions" }),
		);
		await user.click(
			screen.getByRole("menuitem", { name: /rebuild sdk/i }),
		);

		expect(onUpdateSdk).toHaveBeenCalledOnce();
	});

	it("offers retry when the tracked SDK update job failed and source is available", async () => {
		const user = userEvent.setup();
		const onUpdateSdk = vi.fn();
		renderSurface({
			apps: [
				makeApp({
					sdk_status: "update_available",
					sdk_source_available: true,
				}),
			],
			getSdkUpdateState: () => "failed",
			onUpdateSdk,
		});

		expect(screen.getByText("SDK update failed")).toBeVisible();

		await user.click(
			screen.getByRole("button", { name: "Dispatch Board actions" }),
		);
		await user.click(
			screen.getByRole("menuitem", { name: /retry sdk update/i }),
		);

		expect(onUpdateSdk).toHaveBeenCalledOnce();
	});

	it("keeps SDK-only actions available for solution-managed table rows", async () => {
		const user = userEvent.setup();
		const onUpdateSdk = vi.fn();
		renderSurface({
			viewMode: "table",
			apps: [
				makeApp({
					is_solution_managed: true,
					solution_id: "sol-1",
				}),
			],
			onUpdateSdk,
			onOpenSettings: vi.fn(),
			onDelete: vi.fn(),
		});

		await user.click(
			screen.getByRole("button", { name: "Dispatch Board actions" }),
		);

		expect(
			screen.getByRole("menuitem", { name: /update sdk/i }),
		).toBeVisible();
		expect(screen.queryByRole("menuitem", { name: /settings/i })).toBeNull();
		expect(screen.queryByRole("menuitem", { name: /delete/i })).toBeNull();
	});
});
