import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import {
	WorkflowListSurface,
	type WorkflowListItem,
} from "./WorkflowListSurface";

describe("workflow recovery actions", () => {
	it.each(["grid", "table"] as const)(
		"keeps endpoint and missing-file actions keyboard accessible in %s",
		async (viewMode) => {
			const workflow = {
				id: "review-workflow",
				name: "review_workflow",
				type: "workflow",
				endpoint_enabled: true,
				is_orphaned: true,
			} as WorkflowListItem;
			const onEditEndpoint = vi.fn();
			const onResolveOrphaned = vi.fn();
			const onExecute = vi.fn();
			const { user } = renderWithProviders(
				<WorkflowListSurface
					workflows={[workflow]}
					viewMode={viewMode}
					isPlatformAdmin
					canManageWorkflows
					getOrgName={() => "Global"}
					onEditEndpoint={onEditEndpoint}
					onResolveOrphaned={onResolveOrphaned}
					onExecute={onExecute}
				/>,
			);
			expect(
				screen.getByRole("link", { name: "review_workflow" }),
			).toHaveAttribute("href", "/history?workflow=review-workflow");
			const menu = screen.getByRole("button", {
				name: "review_workflow actions",
			});
			menu.focus();
			await user.keyboard("{Enter}");
			screen.getByRole("menuitem", { name: "Edit endpoint" }).focus();
			await user.keyboard("{Enter}");
			expect(onEditEndpoint).toHaveBeenCalledExactlyOnceWith(workflow);
			await user.click(menu);
			screen
				.getByRole("menuitem", { name: "Resolve missing file" })
				.focus();
			await user.keyboard("{Enter}");
			expect(onResolveOrphaned).toHaveBeenCalledExactlyOnceWith(workflow);
			expect(onExecute).not.toHaveBeenCalled();
		},
	);
});
