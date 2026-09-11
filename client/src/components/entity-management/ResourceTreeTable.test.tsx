import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { ResourceTreeTable } from "./ResourceTreeTable";
import type { EntityWithScope, Organization, Role } from "./types";

const dependencyGraph = vi.fn();

vi.mock("@/hooks/useDependencyGraph", () => ({
	useDependencyGraph: (entityType?: string, entityId?: string) =>
		dependencyGraph(entityType, entityId),
}));

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

it("loads relationships from the expanded row and preserves the root list", async () => {
	const user = userEvent.setup();
	const onVisibleKeysChange = vi.fn();
	dependencyGraph.mockReturnValue({
		data: {
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
		},
		isLoading: false,
		isError: false,
		isFetching: false,
		refetch: vi.fn(),
	});

	renderTable({
		entities: entities.slice(0, 1),
		allEntities: entities,
		onVisibleKeysChange,
	});
	expect(onVisibleKeysChange).toHaveBeenLastCalledWith(["app:app-1"]);
	await user.click(
		screen.getAllByRole("button", { name: "Expand Covi Portal" })[0],
	);

	expect(dependencyGraph).toHaveBeenLastCalledWith("app", "app-1");
	const rows = screen.getAllByRole("row");
	expect(rows).toHaveLength(4);
	expect(rows[1]).toHaveTextContent("Covi Portal");
	expect(rows[2]).toHaveTextContent("Create service request");
	expect(rows[2]).toHaveTextContent("Used by Covi Portal");
	expect(rows[3]).toHaveTextContent("Service request form");
	expect(rows[3]).toHaveTextContent("Uses Create service request");
	expect(onVisibleKeysChange).toHaveBeenLastCalledWith([
		"app:app-1",
		"workflow:workflow-1",
		"form:form-1",
	]);
	await user.click(
		screen.getAllByRole("button", { name: "Collapse Covi Portal" })[0],
	);
	expect(screen.getAllByRole("row")).toHaveLength(2);
	expect(onVisibleKeysChange).toHaveBeenLastCalledWith(["app:app-1"]);
});

it("keeps composite selection distinct and routes delete actions with actual ids", async () => {
	const user = userEvent.setup();
	const onSelect = vi.fn();
	const onDelete = vi.fn();
	dependencyGraph.mockReturnValue({
		data: null,
		isLoading: false,
		isError: false,
		isFetching: false,
		refetch: vi.fn(),
	});
	renderTable({
		entities: [
			entity("shared", "Portal", "app", null, "authenticated"),
			entity(
				"shared",
				"Provision customer",
				"workflow",
				null,
				"authenticated",
			),
		],
		allEntities: [
			entity("shared", "Portal", "app", null, "authenticated"),
			entity(
				"shared",
				"Provision customer",
				"workflow",
				null,
				"authenticated",
			),
		],
		selectedIds: new Set(["workflow:shared"]),
		onSelect,
		onDelete,
	});
	const rows = screen.getAllByRole("row");
	expect(within(rows[1]).getByRole("checkbox")).not.toBeChecked();
	expect(within(rows[2]).getByRole("checkbox")).toBeChecked();
	await user.click(within(rows[1]).getByRole("checkbox"));
	expect(onSelect).toHaveBeenCalledWith("app:shared", true);
	await user.click(
		within(rows[1]).getByRole("button", { name: "More actions for Portal" }),
	);
	await user.click(screen.getByRole("menuitem", { name: "Delete app" }));
	expect(onDelete).toHaveBeenCalledWith("shared", "Portal", "app");
});

it("shows loading and error states inline on the expanded row", async () => {
	const user = userEvent.setup();
	const refetch = vi.fn();
	dependencyGraph.mockReturnValue({
		data: null,
		isLoading: true,
		isError: false,
		isFetching: false,
		refetch,
	});
	const { rerender } = renderTable({ entities: entities.slice(0, 1), allEntities: entities });
	await user.click(
		screen.getAllByRole("button", { name: "Expand Covi Portal" })[0],
	);
	expect(screen.getAllByRole("button", { name: "Collapse Covi Portal" })[0]).toHaveAttribute("aria-expanded", "true");
	dependencyGraph.mockReturnValue({
		data: null,
		isLoading: false,
		isError: true,
		isFetching: false,
		refetch,
	});
	rerender(table({ entities: entities.slice(0, 1), allEntities: entities }));
	expect(screen.getAllByRole("row")[1]).toHaveTextContent("Could not load related resources");
	await user.click(screen.getAllByRole("button", { name: "Retry" })[0]);
	expect(refetch).toHaveBeenCalled();
});

it("shows an inline empty relationships state when expansion has no children", async () => {
	const user = userEvent.setup();
	dependencyGraph.mockReturnValue({
		data: {
			root_id: "app:app-1",
			nodes: [],
			edges: [],
		},
		isLoading: false,
		isError: false,
		isFetching: false,
		refetch: vi.fn(),
	});
	renderTable({ entities: entities.slice(0, 1), allEntities: entities });
	await user.click(
		screen.getAllByRole("button", { name: "Expand Covi Portal" })[0],
	);
	expect(screen.getAllByRole("row")[1]).toHaveTextContent(
		"No related resources",
	);
});

function renderTable(overrides: Partial<TableProps> = {}) {
	return render(table(overrides));
}

function table(overrides: Partial<TableProps> = {}) {
	const props: TableProps = {
		entities,
		allEntities: entities,
		selectedIds: new Set(),
		onSelect: vi.fn(),
		onDelete: vi.fn(),
		onVisibleKeysChange: vi.fn(),
		...overrides,
	};
	return (
		<ResourceTreeTable
			entities={props.entities}
			allEntities={props.allEntities}
			organizations={organizations}
			roles={roles}
			selectedIds={props.selectedIds}
			allSelected={false}
			someSelected={props.selectedIds.size > 0}
			onSelectAll={vi.fn()}
			onSelect={props.onSelect}
			onVisibleKeysChange={props.onVisibleKeysChange}
			onDelete={props.onDelete}
		/>
	);
}

interface TableProps {
	entities: EntityWithScope[];
	allEntities: EntityWithScope[];
	selectedIds: Set<string>;
	onSelect: (entityKey: string, selected: boolean) => void;
	onVisibleKeysChange: (entityKeys: string[]) => void;
	onDelete: (
		entityId: string,
		entityName: string,
		entityType: EntityWithScope["entityType"],
	) => void;
}

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
