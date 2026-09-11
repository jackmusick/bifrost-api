import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, it, vi } from "vitest";

import { EntityManagement } from "./EntityManagement";

const authFetch = vi.hoisted(() => vi.fn());
const apiPost = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api-client", () => ({
	authFetch: (...args: unknown[]) => authFetch(...args),
	apiClient: { POST: (...args: unknown[]) => apiPost(...args) },
}));

vi.mock("sonner", () => ({
	toast: {
		success: vi.fn(),
		error: vi.fn(),
	},
}));

vi.mock("@/hooks/useWorkflows", () => ({
	useWorkflows: () => ({
		data: [
			{
				id: "workflow-1",
				name: "Create service request",
				organization_id: null,
				access_level: "authenticated",
				created_at: "2026-01-01T00:00:00Z",
				used_by_count: 1,
				is_solution_managed: false,
				solution_id: null,
			},
		],
		isLoading: false,
		isError: false,
		isFetching: false,
		refetch: vi.fn(),
	}),
	useUpdateWorkflow: () => ({ mutateAsync: vi.fn() }),
}));

vi.mock("@/hooks/useForms", () => ({
	useForms: () => ({
		data: [
			{
				id: "form-1",
				name: "Service request intake",
				organization_id: null,
				access_level: "authenticated",
				created_at: "2026-01-01T00:00:00Z",
				dependency_count: 1,
				is_active: true,
				is_solution_managed: false,
				solution_id: null,
			},
		],
		isLoading: false,
		isError: false,
		isFetching: false,
		refetch: vi.fn(),
	}),
	useUpdateForm: () => ({ mutateAsync: vi.fn() }),
}));

vi.mock("@/hooks/useAgents", () => ({
	useAgents: () => ({
		data: [],
		isLoading: false,
		isError: false,
		isFetching: false,
		refetch: vi.fn(),
	}),
	useUpdateAgent: () => ({ mutateAsync: vi.fn() }),
}));

vi.mock("@/hooks/useApplications", () => ({
	useApplications: () => ({
		data: {
			applications: [
				{
					id: "app-1",
					name: "Covi Portal",
					slug: "covi-portal",
					organization_id: null,
					access_level: "authenticated",
					role_ids: [],
					created_at: "2026-01-01T00:00:00Z",
					is_solution_managed: false,
					solution_id: null,
				},
			],
		},
		isLoading: false,
		isError: false,
		isFetching: false,
		refetch: vi.fn(),
	}),
	useUpdateApplication: () => ({ mutateAsync: vi.fn() }),
}));

vi.mock("@/hooks/useOrganizations", () => ({
	useOrganizations: () => ({
		data: [],
		isLoading: false,
		isError: false,
		isFetching: false,
		refetch: vi.fn(),
	}),
}));

vi.mock("@/hooks/useRoles", () => ({
	useRoles: () => ({
		data: [],
		isLoading: false,
		isError: false,
		isFetching: false,
		refetch: vi.fn(),
	}),
}));

vi.mock("@/hooks/useDependencyGraph", () => ({
	useDependencyGraph: (entityType?: string, entityId?: string) => ({
		data:
			entityType === "app" && entityId === "app-1"
				? {
						root_id: "app:app-1",
						nodes: [
							{
								id: "app:app-1",
								type: "app",
								name: "Covi Portal",
								org_id: null,
							},
							{
								id: "workflow:workflow-1",
								type: "workflow",
								name: "Create service request",
								org_id: null,
							},
							{
								id: "form:form-1",
								type: "form",
								name: "Service request intake",
								org_id: null,
							},
						],
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
					}
				: undefined,
		isLoading: false,
		isError: false,
		isFetching: false,
		refetch: vi.fn(),
	}),
}));

vi.mock("@/hooks/useAssignEntityRole", () => ({
	useAssignEntityRole: () => vi.fn(),
}));

it("expands related resources inline from a search result", async () => {
	const user = userEvent.setup();
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	apiPost.mockResolvedValue({
		data: {
			has_relationships: {
				"app:app-1": true,
				"workflow:workflow-1": true,
				"form:form-1": true,
			},
		},
	});
	render(
		<QueryClientProvider client={queryClient}>
			<EntityManagement />
		</QueryClientProvider>,
	);

	await user.type(
		screen.getByRole("textbox", { name: "Search entities" }),
		"Covi",
	);
	expect(screen.getAllByText("Covi Portal").length).toBeGreaterThan(0);
	expect(
		screen.queryByText("Create service request"),
	).not.toBeInTheDocument();

	const expandButtons = await screen.findAllByRole("button", {
		name: "Expand Covi Portal",
	});
	await user.click(expandButtons[0]);

	expect(
		screen.getByRole("textbox", { name: "Search entities" }),
	).toHaveValue("Covi");
	expect(
		screen.getAllByText("Create service request").length,
	).toBeGreaterThan(0);
	expect(
		screen.getAllByText("Service request intake").length,
	).toBeGreaterThan(0);

	await user.click(
		screen.getAllByRole("checkbox", {
			name: "Select all visible entities",
		})[0],
	);
	expect(screen.getByText("3 selected")).toBeInTheDocument();
	await user.clear(screen.getByRole("textbox", { name: "Search entities" }));
	await user.type(
		screen.getByRole("textbox", { name: "Search entities" }),
		"No matching resource",
	);
	expect(screen.getByRole("status")).toHaveTextContent(
		"3 selected (3 outside this view)",
	);
});
