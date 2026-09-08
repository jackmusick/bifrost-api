import { describe, expect, it, vi } from "vitest";
import { useLocation } from "react-router-dom";
import { renderWithProviders, screen } from "@/test-utils";
import {
	WorkflowListSurface,
	type WorkflowListItem,
} from "./WorkflowListSurface";

function LocationProbe() {
	const location = useLocation();
	return (
		<output aria-label="location">
			{location.pathname + location.search}
		</output>
	);
}

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

	it("opens the workflow history filter from the table row", async () => {
		const workflow = {
			id: "review-workflow",
			name: "review_workflow",
			type: "workflow",
		} as WorkflowListItem;
		const { user } = renderWithProviders(
			<>
				<WorkflowListSurface
					workflows={[workflow]}
					viewMode="table"
					isPlatformAdmin
					canManageWorkflows
					getOrgName={() => "Global"}
					onExecute={vi.fn()}
				/>
				<LocationProbe />
			</>,
		);

		await user.click(screen.getByRole("row", { name: /review_workflow/i }));

		expect(screen.getByLabelText("location")).toHaveTextContent(
			"/history?workflow=review-workflow",
		);
	});
});
