/**
 * Component tests for UserDetailsDialog.
 *
 * Covers:
 * - shows user name + email in header
 * - Platform Admin badge and full-access card for superusers
 * - Active / Inactive status badge
 * - role + form tabs only render for org users with an organization
 * - empty state for roles list
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";

const mockUserRoles = vi.fn();
const mockUserForms = vi.fn();

vi.mock("@/hooks/useUsers", () => ({
	useUserRoles: () => mockUserRoles(),
	useUserForms: () => mockUserForms(),
}));

import { UserDetailsDialog } from "./UserDetailsDialog";

type User = Parameters<typeof UserDetailsDialog>[0]["user"];

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

beforeEach(() => {
	mockUserRoles.mockReset();
	mockUserForms.mockReset();
	mockUserRoles.mockReturnValue({ data: { role_ids: [] }, isLoading: false });
	mockUserForms.mockReturnValue({ data: { form_ids: [] }, isLoading: false });
});

describe("UserDetailsDialog", () => {
	it("renders the user name and email in the header", () => {
		renderWithProviders(
			<UserDetailsDialog
				user={makeUser()}
				open={true}
				onClose={vi.fn()}
			/>,
		);

		expect(
			screen.getByRole("heading", { name: /alice/i }),
		).toBeInTheDocument();
		expect(
			screen.getByText(/alice@example.com/i),
		).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: /close dialog/i }),
		).toBeInTheDocument();
	});

	it("shows Platform Admin badge + full access card for superusers", () => {
		renderWithProviders(
			<UserDetailsDialog
				user={makeUser({ is_superuser: true, organization_id: null })}
				open={true}
				onClose={vi.fn()}
			/>,
		);

		expect(screen.getByText(/platform admin/i)).toBeInTheDocument();
		expect(screen.getByText(/full platform access/i)).toBeInTheDocument();
		// Roles/Forms tabs only render for org users — should NOT show here.
		expect(
			screen.queryByRole("tab", { name: /roles/i }),
		).not.toBeInTheDocument();
	});

	it("shows Active status badge when user is active", () => {
		renderWithProviders(
			<UserDetailsDialog
				user={makeUser()}
				open={true}
				onClose={vi.fn()}
			/>,
		);

		expect(screen.getByText(/^active$/i)).toBeInTheDocument();
		expect(screen.getByText(/^active$/i)).toHaveAttribute(
			"data-variant",
			"outline",
		);
	});

	it("shows Inactive badge when user is inactive", () => {
		renderWithProviders(
			<UserDetailsDialog
				user={makeUser({ is_active: false })}
				open={true}
				onClose={vi.fn()}
			/>,
		);

		expect(screen.getByText(/^inactive$/i)).toBeInTheDocument();
	});

	it("renders Roles + Form Access tabs for org users", () => {
		renderWithProviders(
			<UserDetailsDialog
				user={makeUser()}
				open={true}
				onClose={vi.fn()}
			/>,
		);

		expect(screen.getByRole("tab", { name: /roles/i })).toBeInTheDocument();
		expect(
			screen.getByRole("tab", { name: /form access/i }),
		).toBeInTheDocument();
	});

	it("shows an empty state when the user has no assigned roles", () => {
		renderWithProviders(
			<UserDetailsDialog
				user={makeUser()}
				open={true}
				onClose={vi.fn()}
			/>,
		);

		expect(
			screen.getByText(/no roles assigned to this user/i),
		).toBeInTheDocument();
	});

	it("shows a distinct error state when roles fail to load", async () => {
		const retry = vi.fn();
		mockUserRoles.mockReturnValue({
			error: new Error("Roles API down"),
			refetch: retry,
			isLoading: false,
		});

		const { user } = renderWithProviders(
			<UserDetailsDialog
				user={makeUser()}
				open={true}
				onClose={vi.fn()}
			/>,
		);

		expect(
			screen.getByRole("alert", { name: /unable to load roles/i }),
		).toBeInTheDocument();
		await user.click(screen.getByRole("button", { name: "Retry" }));
		expect(retry).toHaveBeenCalledOnce();
		expect(screen.getByText(/roles api down/i)).toBeInTheDocument();
		expect(
			screen.queryByText(/no roles assigned to this user/i),
		).not.toBeInTheDocument();
	});

	it("shows a distinct error state when forms fail to load", async () => {
		mockUserForms.mockReturnValue({
			error: new Error("Forms API down"),
			isLoading: false,
		});

		const { user } = renderWithProviders(
			<UserDetailsDialog
				user={makeUser()}
				open={true}
				onClose={vi.fn()}
			/>,
		);

		await user.click(screen.getByRole("tab", { name: /form access/i }));
		expect(
			screen.getByRole("alert", { name: /unable to load form access/i }),
		).toBeInTheDocument();
		expect(screen.getByText(/forms api down/i)).toBeInTheDocument();
		expect(
			screen.queryByText(/no forms accessible to this user/i),
		).not.toBeInTheDocument();
	});
});
