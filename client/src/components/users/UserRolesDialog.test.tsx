/**
 * Component tests for UserRolesDialog.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderWithProviders, screen, waitFor } from "@/test-utils";

const mockUserRoles = vi.fn();
const mockRoles = vi.fn();
const mockAssignMutate = vi.fn();
const mockRemoveMutate = vi.fn();
const mockRefetchUserRoles = vi.fn();
const mockRefetchRoles = vi.fn();

vi.mock("@/hooks/useUsers", () => ({
	useUserRoles: () => mockUserRoles(),
}));

vi.mock("@/hooks/useRoles", () => ({
	useRoles: () => mockRoles(),
	useAssignUsersToRole: () => ({
		mutateAsync: mockAssignMutate,
		isPending: false,
	}),
	useRemoveUserFromRole: () => ({
		mutateAsync: mockRemoveMutate,
		isPending: false,
	}),
}));

import { UserRolesDialog } from "./UserRolesDialog";

type User = Parameters<typeof UserRolesDialog>[0]["user"];

type QueryState<T> = {
	data: T | undefined;
	isLoading: boolean;
	isError: boolean;
	error?: unknown;
	refetch: () => Promise<unknown>;
};

function makeUser(overrides: Partial<NonNullable<User>> = {}): NonNullable<User> {
	return {
		id: "u-1",
		email: "alice@example.com",
		name: "Alice",
		is_active: true,
		is_superuser: false,
		organization_id: "org-1",
		created_at: "2026-04-20T00:00:00Z",
		updated_at: "2026-04-20T00:00:00Z",
		last_login: null,
		...overrides,
	} as NonNullable<User>;
}

const userRolesState: QueryState<{ role_ids: string[] }> = {
	data: { role_ids: [] },
	isLoading: false,
	isError: false,
	refetch: mockRefetchUserRoles,
};

const rolesState: QueryState<Array<{ id: string; name: string; description: string | null }>> = {
	data: [],
	isLoading: false,
	isError: false,
	refetch: mockRefetchRoles,
};

function setUserRolesState(overrides: Partial<QueryState<{ role_ids: string[] }>>) {
	Object.assign(userRolesState, overrides);
}

function setRolesState(
	overrides: Partial<QueryState<Array<{ id: string; name: string; description: string | null }>>>,
) {
	Object.assign(rolesState, overrides);
}

function setLoadedData(roleIds: string[], roles: Array<{ id: string; name: string; description: string | null }>) {
	setUserRolesState({
		data: { role_ids: roleIds },
		isLoading: false,
		isError: false,
		error: undefined,
	});
	setRolesState({
		data: roles,
		isLoading: false,
		isError: false,
		error: undefined,
	});
}

beforeEach(() => {
	mockUserRoles.mockReset();
	mockUserRoles.mockImplementation(() => userRolesState);
	mockRoles.mockReset();
	mockRoles.mockImplementation(() => rolesState);
	mockAssignMutate.mockReset();
	mockAssignMutate.mockResolvedValue({});
	mockRemoveMutate.mockReset();
	mockRemoveMutate.mockResolvedValue({});
	mockRefetchUserRoles.mockReset();
	mockRefetchUserRoles.mockResolvedValue({});
	mockRefetchRoles.mockReset();
	mockRefetchRoles.mockResolvedValue({});
	setLoadedData([], []);
});

describe("UserRolesDialog", () => {
	it("shows the superuser notice for superusers", () => {
		setLoadedData([], []);

		renderWithProviders(
			<UserRolesDialog
				user={makeUser({ is_superuser: true })}
				open={true}
				onClose={vi.fn()}
			/>,
		);

		expect(screen.getByText(/cannot modify superuser roles/i)).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /close dialog/i })).toBeInTheDocument();
	});

	it("hydrates checked state after the roles query settles", async () => {
		setUserRolesState({
			data: undefined,
			isLoading: true,
			isError: false,
			error: undefined,
		});
		setRolesState({
			data: [
				{ id: "r-1", name: "Admin", description: "Admin role" },
				{ id: "r-2", name: "Viewer", description: "Viewer role" },
			],
			isLoading: false,
			isError: false,
			error: undefined,
		});
		const { rerender } = renderWithProviders(
			<UserRolesDialog user={makeUser()} open={true} onClose={vi.fn()} />,
		);

		setLoadedData(["r-1"], [
			{ id: "r-1", name: "Admin", description: "Admin role" },
			{ id: "r-2", name: "Viewer", description: "Viewer role" },
		]);
		rerender(<UserRolesDialog user={makeUser()} open={true} onClose={vi.fn()} />);

		expect(screen.getByRole("checkbox", { name: /admin/i })).toBeChecked();
		expect(screen.getByRole("checkbox", { name: /viewer/i })).not.toBeChecked();
	});

	it("preserves local edits while the role queries refetch", async () => {
		setLoadedData(["r-1"], [{ id: "r-1", name: "Admin", description: "Admin role" }]);

		const { user, rerender } = renderWithProviders(
			<UserRolesDialog user={makeUser()} open={true} onClose={vi.fn()} />,
		);

		await user.click(screen.getByRole("checkbox", { name: /admin/i }));
		await waitFor(() => expect(mockRemoveMutate).toHaveBeenCalled());

		rerender(<UserRolesDialog user={makeUser()} open={true} onClose={vi.fn()} />);

		expect(screen.getByRole("checkbox", { name: /admin/i })).not.toBeChecked();
	});

	it("resets the selection when a different user opens the dialog", () => {
		setLoadedData(["r-1"], [{ id: "r-1", name: "Admin", description: "Admin role" }]);

		const { rerender } = renderWithProviders(
			<UserRolesDialog user={makeUser({ id: "u-1" })} open={true} onClose={vi.fn()} />,
		);

		expect(screen.getByRole("checkbox", { name: /admin/i })).toBeChecked();

		setLoadedData([], [{ id: "r-1", name: "Admin", description: "Admin role" }]);
		rerender(
			<UserRolesDialog user={makeUser({ id: "u-2", name: "Bob" })} open={true} onClose={vi.fn()} />,
		);

		expect(screen.getByRole("checkbox", { name: /admin/i })).not.toBeChecked();
	});

	it("shows query errors with a retry action instead of the empty state", async () => {
		setUserRolesState({
			data: undefined,
			isLoading: false,
			isError: true,
			error: new Error("roles unavailable"),
		});
		setRolesState({
			data: undefined,
			isLoading: false,
			isError: false,
			error: undefined,
		});

		const { user } = renderWithProviders(
			<UserRolesDialog user={makeUser()} open={true} onClose={vi.fn()} />,
		);

		expect(screen.getByRole("alert")).toHaveTextContent(/could not load roles/i);
		expect(screen.queryByText(/no roles available/i)).not.toBeInTheDocument();

		await user.click(screen.getByRole("button", { name: /retry/i }));
		expect(mockRefetchUserRoles).toHaveBeenCalled();
		expect(mockRefetchRoles).toHaveBeenCalled();
	});

	it("calls assignUsersToRole when toggling an unchecked role", async () => {
		setLoadedData([], [{ id: "r-1", name: "Admin", description: null }]);

		const { user } = renderWithProviders(
			<UserRolesDialog user={makeUser()} open={true} onClose={vi.fn()} />,
		);

		await user.click(screen.getByRole("checkbox", { name: /admin/i }));

		await waitFor(() => expect(mockAssignMutate).toHaveBeenCalled());
		expect(mockAssignMutate.mock.calls[0]![0]).toEqual({
			params: { path: { role_id: "r-1" } },
			body: { user_ids: ["u-1"] },
		});
	});

	it("blocks duplicate toggles while a mutation is pending", async () => {
		setLoadedData([], [{ id: "r-1", name: "Admin", description: null }]);
		mockAssignMutate.mockImplementationOnce(() => new Promise(() => {}));

		const { user } = renderWithProviders(
			<UserRolesDialog user={makeUser()} open={true} onClose={vi.fn()} />,
		);

		const checkbox = screen.getByRole("checkbox", { name: /admin/i });
		await user.click(checkbox);
		await user.click(checkbox);

		expect(mockAssignMutate).toHaveBeenCalledTimes(1);
	});

	it("calls removeUserFromRole when unchecking an assigned role", async () => {
		setLoadedData(["r-1"], [{ id: "r-1", name: "Admin", description: null }]);

		const { user } = renderWithProviders(
			<UserRolesDialog user={makeUser()} open={true} onClose={vi.fn()} />,
		);

		await user.click(screen.getByRole("checkbox", { name: /admin/i }));

		await waitFor(() => expect(mockRemoveMutate).toHaveBeenCalled());
		expect(mockRemoveMutate.mock.calls[0]![0]).toEqual({
			params: { path: { role_id: "r-1", user_id: "u-1" } },
		});
	});

	it("shows an inline retryable error when a role mutation fails", async () => {
		setLoadedData([], [{ id: "r-1", name: "Admin", description: null }]);
		mockAssignMutate.mockRejectedValueOnce(new Error("permission denied"));
		mockAssignMutate.mockResolvedValueOnce({});

		const { user } = renderWithProviders(
			<UserRolesDialog user={makeUser()} open={true} onClose={vi.fn()} />,
		);

		await user.click(screen.getByRole("checkbox", { name: /admin/i }));
		expect(screen.getByRole("alert")).toHaveTextContent(/failed to assign role/i);
		expect(screen.getByText(/permission denied/i)).toBeInTheDocument();

		await user.click(screen.getByRole("button", { name: /dismiss/i }));
		expect(screen.queryByRole("alert")).not.toBeInTheDocument();
	});

	it("shows 'No roles available' when roles list is empty", () => {
		setLoadedData([], []);

		renderWithProviders(
			<UserRolesDialog user={makeUser()} open={true} onClose={vi.fn()} />,
		);

		expect(screen.getByText(/no roles available/i)).toBeInTheDocument();
	});
});
