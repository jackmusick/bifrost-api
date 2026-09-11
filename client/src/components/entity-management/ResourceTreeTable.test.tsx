import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { ResourceTreeTable } from "./ResourceTreeTable";
import type { EntityWithScope, Organization, Role } from "./types";

const entities = [
	entity("app-1", "Covi Portal", "app", "org-1", "role_based"),
	entity(
		"workflow-1",
		"Create service request",
		"workflow",
		null,
		"authenticated",
	),
	entity("form-1", "Service request form", "form", "org-1", "authenticated"),
	entity("agent-1", "Support assistant", "agent", "org-1", "role_based"),
];

const organizations = [{ id: "org-1", name: "Northwind" }] as Organization[];
const roles = [{ id: "role-1", name: "Service Desk" }] as Role[];

it("renders focused dependency rows from graph edges without inventing unrelated hierarchy", () => {
	render(
		<ResourceTreeTable
			entities={entities}
			organizations={organizations}
			roles={roles}
			selectedIds={new Set(["workflow:workflow-1"])}
			allSelected={false}
			someSelected
			onSelectAll={vi.fn()}
			onSelect={vi.fn()}
			onShowRelationships={vi.fn()}
			onDelete={vi.fn()}
			focusedEntityId="app-1"
			graphData={{
				root_id: "app:app-1",
				nodes: [],
				edges: [
					{
						source: "app:app-1",
						target: "workflow:workflow-1",
						relationship: "uses",
					},
					{
						source: "form:form-1",
						target: "workflow:workflow-1",
						relationship: "uses",
					},
				],
			}}
		/>,
	);

	const rows = screen.getAllByRole("row");
	expect(rows[1]).toHaveTextContent("Covi Portal");
	expect(rows[2]).toHaveTextContent("Create service request");
	expect(rows[2]).toHaveTextContent("Used by Covi Portal");
	expect(rows[3]).toHaveTextContent("Service request form");
	expect(rows[3]).toHaveTextContent("Uses Create service request");
	expect(rows).toHaveLength(4);
	expect(screen.queryByText("Support assistant")).not.toBeInTheDocument();
	expect(
		within(rows[2]).getByRole("checkbox", {
			name: "Select Create service request",
		}),
	).toBeChecked();
});

it("can expand incoming used-by relationships from composite graph ids", async () => {
	const user = userEvent.setup();
	render(
		<ResourceTreeTable
			entities={entities}
			organizations={organizations}
			roles={roles}
			selectedIds={new Set()}
			allSelected={false}
			someSelected={false}
			onSelectAll={vi.fn()}
			onSelect={vi.fn()}
			onShowRelationships={vi.fn()}
			onDelete={vi.fn()}
			focusedEntityId="workflow-1"
			graphData={{
				root_id: "workflow:workflow-1",
				nodes: [
					{
						id: "workflow:workflow-1",
						type: "workflow",
						name: "Create service request",
						org_id: null,
					},
					{
						id: "form:form-1",
						type: "form",
						name: "Service request form",
						org_id: "org-1",
					},
					{
						id: "agent:agent-1",
						type: "agent",
						name: "Support assistant",
						org_id: "org-1",
					},
				],
				edges: [
					{
						source: "form:form-1",
						target: "workflow:workflow-1",
						relationship: "uses",
					},
					{
						source: "agent:agent-1",
						target: "workflow:workflow-1",
						relationship: "uses",
					},
				],
			}}
		/>,
	);

	expect(screen.getAllByRole("row")[1]).toHaveTextContent(
		"Create service request",
	);
	expect(screen.getAllByRole("row")[2]).toHaveTextContent(
		"Service request form",
	);
	expect(screen.getAllByRole("row")[2]).toHaveTextContent(
		"Uses Create service request",
	);
	await user.click(
		screen.getAllByRole("button", {
			name: "Collapse Create service request",
		})[0],
	);
	expect(screen.getAllByRole("row")).toHaveLength(2);
	await user.click(
		screen.getAllByRole("button", {
			name: "Expand Create service request",
		})[0],
	);
	expect(screen.getAllByRole("row")[2]).toHaveTextContent(
		"Service request form",
	);
});

it("routes selection, relationship focus, and delete actions from the table", async () => {
	const user = userEvent.setup();
	const onSelectAll = vi.fn();
	const onSelect = vi.fn();
	const onShowRelationships = vi.fn();
	const onDelete = vi.fn();
	render(
		<ResourceTreeTable
			entities={entities.slice(0, 1)}
			organizations={organizations}
			roles={roles}
			selectedIds={new Set()}
			allSelected={false}
			someSelected={false}
			onSelectAll={onSelectAll}
			onSelect={onSelect}
			onShowRelationships={onShowRelationships}
			onDelete={onDelete}
		/>,
	);

	await user.click(
		screen.getByRole("checkbox", { name: "Select all visible entities" }),
	);
	expect(onSelectAll).toHaveBeenCalledWith(true);
	await user.click(
		screen.getAllByRole("checkbox", { name: "Select Covi Portal" })[0],
	);
	expect(onSelect).toHaveBeenCalledWith("app:app-1", true);
	await user.click(
		screen.getAllByRole("button", {
			name: "Focus relationships for Covi Portal",
		})[0],
	);
	expect(onShowRelationships).toHaveBeenCalledWith(
		"app-1",
		"app",
		"Covi Portal",
	);
	await user.click(
		screen.getAllByRole("button", {
			name: "More actions for Covi Portal",
		})[0],
	);
	await user.click(screen.getByRole("menuitem", { name: "Delete app" }));
	expect(onDelete).toHaveBeenCalledWith("app-1", "Covi Portal", "app");
});

it("keeps resources with the same UUID distinct when focusing and selecting", async () => {
	const onSelect = vi.fn();
	render(
		<ResourceTreeTable
			entities={[
				entity("shared", "Portal", "app", null, "authenticated"),
				entity(
					"shared",
					"Provision customer",
					"workflow",
					null,
					"authenticated",
				),
			]}
			organizations={[]}
			roles={[]}
			selectedIds={new Set(["workflow:shared"])}
			allSelected={false}
			someSelected
			onSelectAll={vi.fn()}
			onSelect={onSelect}
			onShowRelationships={vi.fn()}
			onDelete={vi.fn()}
			focusedEntityId="shared"
			graphData={{
				root_id: "workflow:shared",
				nodes: [],
				edges: [
					{
						source: "app:shared",
						target: "workflow:shared",
						relationship: "uses",
					},
				],
			}}
		/>,
	);
	const rows = screen.getAllByRole("row");
	expect(rows[1]).toHaveTextContent("Provision customer");
	expect(within(rows[1]).getByRole("checkbox")).toBeChecked();
	expect(within(rows[2]).getByRole("checkbox")).not.toBeChecked();
	await userEvent.setup().click(within(rows[2]).getByRole("checkbox"));
	expect(onSelect).toHaveBeenCalledWith("app:shared", true);
});

function entity(
	id: string,
	name: string,
	entityType: EntityWithScope["entityType"],
	organizationId: string | null,
	accessLevel: string | null,
): EntityWithScope {
	return {
		key: `${entityType}:${id}`,
		id,
		name,
		entityType,
		organizationId,
		accessLevel,
		roleIds: entityType === "app" ? ["role-1"] : [],
		createdAt: "2026-01-01T00:00:00Z",
		usedByCount: entityType === "app" ? null : 1,
		original: {},
	} as EntityWithScope;
}
