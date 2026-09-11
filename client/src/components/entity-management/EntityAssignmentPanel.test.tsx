import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { EntityAssignmentPanel } from "./EntityAssignmentPanel";
import type { EntityWithScope, Organization, Role } from "./types";

vi.mock("@/components/forms/OrganizationSelect", () => ({
	OrganizationSelect: ({
		onChange,
		disabled,
	}: {
		onChange: (value: string | null) => void;
		disabled?: boolean;
	}) => (
		<button
			type="button"
			disabled={disabled}
			onClick={() => onChange("org-1")}
		>
			Northwind
		</button>
	),
}));

it("reviews scope and additive access changes, then applies both to the frozen selection", async () => {
	const user = userEvent.setup();
	const onOrganization = vi.fn().mockResolvedValue(undefined);
	const onAccess = vi.fn().mockResolvedValue(undefined);
	const props = {
		entities: [
			entity(
				"workflow:a",
				"Create service request",
				"workflow",
				null,
				"private",
				[],
			),
			entity(
				"agent:b",
				"Support assistant",
				"agent",
				"org-1",
				"role_based",
				["role-2"],
			),
		],
		organizations,
		roles,
		disabled: false,
		onOrganization,
		onAccess,
		selectedIds: new Set(["workflow:a", "agent:b"]),
	};
	const { rerender } = render(<EntityAssignmentPanel {...props} />);

	await user.click(
		screen.getByRole("combobox", { name: "Organization change mode" }),
	);
	await user.click(screen.getByRole("option", { name: "Set scope" }));
	await user.click(screen.getByRole("button", { name: "Northwind" }));
	await user.click(screen.getByRole("combobox", { name: "Access change" }));
	await user.click(
		screen.getByRole("option", { name: "Add role: Service Desk" }),
	);

	expect(
		screen.getByText("Create service request").closest("li"),
	).toHaveTextContent("Scope: Global -> Northwind");
	expect(
		screen.getByText("Create service request").closest("li"),
	).toHaveTextContent("Access: Private -> Add role Service Desk");
	expect(
		screen.getByText("Support assistant").closest("li"),
	).toHaveTextContent("Scope: No change (Northwind)");
	expect(
		screen.getByText("Support assistant").closest("li"),
	).toHaveTextContent(
		"Access: Existing Role -> Existing Role, add Service Desk",
	);

	const apply = screen.getByRole("button", { name: "Apply changes" });
	await user.click(apply);
	rerender(
		<EntityAssignmentPanel
			{...props}
			selectedIds={new Set(["workflow:other"])}
		/>,
	);

	await waitFor(() =>
		expect(onOrganization).toHaveBeenCalledWith(
			["workflow:a", "agent:b"],
			"org-1",
		),
	);
	expect(onAccess).toHaveBeenCalledWith(["workflow:a", "agent:b"], "role-1");
});

it("does not apply access or reset review state when the scope phase fails", async () => {
	const user = userEvent.setup();
	const onOrganization = vi.fn().mockRejectedValue(new Error("Scope failed"));
	const onAccess = vi.fn().mockResolvedValue(undefined);
	render(
		<EntityAssignmentPanel
			entities={[
				entity(
					"workflow:a",
					"Create service request",
					"workflow",
					null,
					"authenticated",
					[],
				),
			]}
			organizations={organizations}
			roles={roles}
			disabled={false}
			onOrganization={onOrganization}
			onAccess={onAccess}
			selectedIds={new Set(["workflow:a"])}
		/>,
	);

	await user.click(
		screen.getByRole("combobox", { name: "Organization change mode" }),
	);
	await user.click(screen.getByRole("option", { name: "Set scope" }));
	await user.click(screen.getByRole("button", { name: "Northwind" }));
	await user.click(screen.getByRole("combobox", { name: "Access change" }));
	await user.click(
		screen.getByRole("option", { name: "Everyone except external users" }),
	);
	await user.click(screen.getByRole("button", { name: "Apply changes" }));

	await waitFor(() =>
		expect(screen.getByRole("alert")).toHaveTextContent("Scope failed"),
	);
	expect(onOrganization).toHaveBeenCalledWith(["workflow:a"], "org-1");
	expect(onAccess).not.toHaveBeenCalled();
	expect(
		screen.getByText("Create service request").closest("li"),
	).toHaveTextContent("Scope: Global -> Northwind");
	expect(screen.getByRole("button", { name: "Apply changes" })).toBeEnabled();
});

it("requires a selection and a proposed change", async () => {
	const user = userEvent.setup();
	const onAccess = vi.fn().mockResolvedValue(undefined);
	const { rerender } = render(
		<EntityAssignmentPanel
			entities={[
				entity(
					"workflow:a",
					"Alpha",
					"workflow",
					null,
					"authenticated",
					[],
				),
			]}
			organizations={organizations}
			roles={roles}
			disabled={false}
			onOrganization={vi.fn()}
			onAccess={onAccess}
			selectedIds={new Set()}
		/>,
	);

	expect(
		screen.getByRole("button", { name: "Apply changes" }),
	).toBeDisabled();
	rerender(
		<EntityAssignmentPanel
			entities={[
				entity(
					"workflow:a",
					"Alpha",
					"workflow",
					null,
					"authenticated",
					[],
				),
			]}
			organizations={organizations}
			roles={roles}
			disabled={false}
			onOrganization={vi.fn()}
			onAccess={onAccess}
			selectedIds={new Set(["workflow:a"])}
		/>,
	);
	expect(
		screen.getByRole("button", { name: "Apply changes" }),
	).toBeDisabled();
	await user.click(screen.getByRole("combobox", { name: "Access change" }));
	await user.click(
		screen.getByRole("option", { name: "Everyone except external users" }),
	);
	await user.click(screen.getByRole("button", { name: "Apply changes" }));
	await waitFor(() =>
		expect(onAccess).toHaveBeenCalledWith(["workflow:a"], "authenticated"),
	);
});

const organizations = [
	{
		id: "org-1",
		name: "Northwind",
		is_active: true,
		is_provider: false,
		created_at: null,
		created_by: "test",
		updated_at: null,
	},
] as Organization[];

const roles = [
	{
		id: "role-1",
		name: "Service Desk",
		created_by: "test",
		created_at: null,
		updated_at: null,
	},
	{
		id: "role-2",
		name: "Existing Role",
		created_by: "test",
		created_at: null,
		updated_at: null,
	},
] as Role[];

function entity(
	key: string,
	name: string,
	entityType: EntityWithScope["entityType"],
	organizationId: string | null,
	accessLevel: string | null,
	roleIds: string[],
): EntityWithScope {
	return {
		key,
		id: key.slice(key.indexOf(":") + 1),
		name,
		entityType,
		organizationId,
		accessLevel,
		roleIds,
		createdAt: "2026-01-01T00:00:00Z",
		usedByCount: 0,
		original: {},
	} as EntityWithScope;
}
