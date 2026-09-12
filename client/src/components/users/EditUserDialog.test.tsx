/**
 * Component tests for EditUserDialog.
 *
 * Covers:
 * - pre-fills fields from the user prop
 * - "editing your own account" notice appears when currentUser.id matches
 * - "No changes to save" branch short-circuits on unchanged submit
 * - happy-path submit sends only the name delta
 * - promoting to platform admin surfaces the promote notice
 *
 * The Combobox is stubbed to a <select> for the same reason as
 * CreateUserDialog.test.tsx — driving Radix popovers in happy-dom is slow
 * and brittle.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderWithProviders, screen, waitFor } from "@/test-utils";

const mockUpdateMutate = vi.fn();
const mockAssignMutate = vi.fn();
const mockRemoveMutate = vi.fn();
const mockOrganizations = vi.fn();
const mockRoles = vi.fn();
const mockUserRoles = vi.fn();
const mockAuth = vi.fn();

vi.mock("@/hooks/useUsers", () => ({
	useUpdateUser: () => ({
		mutateAsync: mockUpdateMutate,
		isPending: false,
	}),
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

vi.mock("@/hooks/useOrganizations", () => ({
	useOrganizations: () => mockOrganizations(),
}));

vi.mock("@/contexts/AuthContext", () => ({
	useAuth: () => mockAuth(),
}));

vi.mock("@/components/ui/combobox", () => ({
	Combobox: ({
		id,
		value,
		onValueChange,
		options,
		disabled,
	}: {
		id?: string;
		value?: string;
		onValueChange?: (v: string) => void;
		options: { value: string; label: string }[];
		disabled?: boolean;
	}) => (
		<select
			aria-label={id}
			id={id}
			value={value ?? ""}
			disabled={disabled}
			onChange={(e) => onValueChange?.(e.target.value)}
		>
			<option value="">(none)</option>
			{options.map((opt) => (
				<option key={opt.value} value={opt.value}>
					{opt.label}
				</option>
			))}
		</select>
	),
}));

import { EditUserDialog } from "./EditUserDialog";

type User = Parameters<typeof EditUserDialog>[0]["user"];

function makeUser(
	overrides: Partial<NonNullable<User>> = {},
): NonNullable<User> {
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
	mockUpdateMutate.mockReset();
	mockUpdateMutate.mockResolvedValue({});
	mockAssignMutate.mockReset();
	mockAssignMutate.mockResolvedValue({});
	mockRemoveMutate.mockReset();
	mockRemoveMutate.mockResolvedValue({});
	mockOrganizations.mockReturnValue({
		data: [
			{
				id: "org-1",
				name: "Acme",
				domain: "acme.com",
				is_provider: false,
			},
			{
				id: "org-provider",
				name: "Provider",
				domain: null,
				is_provider: true,
			},
		],
		isLoading: false,
	});
	mockRoles.mockReturnValue({ data: [] });
	mockUserRoles.mockReturnValue({ data: { role_ids: [] } });
	mockAuth.mockReturnValue({
		user: { id: "other-user", email: "admin@example.com" },
	});
});

describe("EditUserDialog", () => {
	it("pre-fills the display name from the user prop", () => {
		renderWithProviders(
			<EditUserDialog
				user={makeUser()}
				open={true}
				onOpenChange={vi.fn()}
			/>,
		);

		expect(screen.getByLabelText(/display name/i)).toHaveValue("Alice");
		expect(screen.getByLabelText(/email address/i)).toBeDisabled();
		expect(
			screen.getByRole("button", { name: /close dialog/i }),
		).toBeInTheDocument();
	});

	it("shows 'editing your own account' notice when editing self", () => {
		const user = makeUser();
		mockAuth.mockReturnValue({ user: { id: user.id, email: user.email } });

		renderWithProviders(
			<EditUserDialog user={user} open={true} onOpenChange={vi.fn()} />,
		);

		expect(
			screen.getByText(/editing your own account/i),
		).toBeInTheDocument();
	});

	it("allows self name edits when the account has no organization", async () => {
		const account = makeUser({ organization_id: null });
		mockAuth.mockReturnValue({
			user: { id: account.id, email: account.email },
		});
		const { user } = renderWithProviders(
			<EditUserDialog user={account} open onOpenChange={vi.fn()} />,
		);
		await user.clear(screen.getByLabelText(/display name/i));
		await user.type(
			screen.getByLabelText(/display name/i),
			"Updated Self Name",
		);
		await user.click(screen.getByRole("button", { name: /save changes/i }));
		await waitFor(() => expect(mockUpdateMutate).toHaveBeenCalled());
		expect(mockUpdateMutate.mock.calls[0][0].body).toMatchObject({
			name: "Updated Self Name",
			organization_id: null,
			is_superuser: null,
			is_active: null,
		});
	});

	it("submits only the name delta when just the name is changed", async () => {
		const onOpenChange = vi.fn();
		const { user } = renderWithProviders(
			<EditUserDialog
				user={makeUser()}
				open={true}
				onOpenChange={onOpenChange}
			/>,
		);

		const nameInput = screen.getByLabelText(/display name/i);
		await user.clear(nameInput);
		await user.type(nameInput, "Alice Updated");

		await user.click(screen.getByRole("button", { name: /save changes/i }));

		await waitFor(() => expect(mockUpdateMutate).toHaveBeenCalled());
		expect(
			screen.getByRole("button", { name: /save changes/i }),
		).toHaveClass("h-11");
		const call = mockUpdateMutate.mock.calls[0]![0];
		expect(call.params).toEqual({ path: { user_id: "u-1" } });
		expect(call.body.name).toBe("Alice Updated");
		// Fields that weren't changed should be null so the API leaves them alone.
		expect(call.body.is_active).toBeNull();
		expect(call.body.is_superuser).toBeNull();
		expect(call.body.organization_id).toBeNull();
		expect(onOpenChange).toHaveBeenCalledWith(false);
	});

	it("does not call update when nothing has changed", async () => {
		const onOpenChange = vi.fn();
		const { user } = renderWithProviders(
			<EditUserDialog
				user={makeUser()}
				open={true}
				onOpenChange={onOpenChange}
			/>,
		);

		await user.click(screen.getByRole("button", { name: /save changes/i }));

		// "No changes to save" short-circuits without hitting the mutation.
		expect(mockUpdateMutate).not.toHaveBeenCalled();
		expect(onOpenChange).toHaveBeenCalledWith(false);
	});

	it("shows the promotion notice when switching to Platform Administrator", async () => {
		const { user } = renderWithProviders(
			<EditUserDialog
				user={makeUser()}
				open={true}
				onOpenChange={vi.fn()}
			/>,
		);

		await user.selectOptions(
			screen.getByLabelText(/userType/i),
			"platform",
		);

		expect(
			await screen.findByText(
				/promoting this user to platform administrator/i,
			),
		).toBeInTheDocument();
	});
});

it("keeps a pending save open and preserves the draft after failure", async () => {
	let rejectSave!: (error: Error) => void;
	mockUpdateMutate.mockImplementationOnce(
		() =>
			new Promise((_resolve, reject) => {
				rejectSave = reject;
			}),
	);
	const onOpenChange = vi.fn();
	const { user } = renderWithProviders(
		<EditUserDialog user={makeUser()} open onOpenChange={onOpenChange} />,
	);
	await user.clear(screen.getByLabelText(/display name/i));
	await user.type(screen.getByLabelText(/display name/i), "Preserved draft");
	await user.click(screen.getByRole("button", { name: "Save Changes" }));
	await user.keyboard("{Escape}");
	expect(onOpenChange).not.toHaveBeenCalled();
	expect(screen.getByRole("button", { name: "Close dialog" })).toBeDisabled();
	expect(
		screen.getByLabelText(/display name/i).closest("[inert]"),
	).not.toBeNull();
	rejectSave(new Error("Synthetic user save failure"));
	const error = await screen.findByRole("alert");
	await waitFor(() => expect(error).toHaveFocus());
	expect(screen.getByLabelText(/display name/i)).toHaveValue(
		"Preserved draft",
	);
	expect(screen.getByRole("button", { name: "Save Changes" })).toBeEnabled();
});

it("requires a recoverable role read before saving another user's access", async () => {
	const refetch = vi.fn().mockResolvedValue({});
	mockUserRoles.mockReturnValue({ isError: true, refetch });
	mockRoles.mockReturnValue({ data: [], refetch });
	const props = { user: makeUser(), open: true, onOpenChange: vi.fn() };
	const { user, rerender } = renderWithProviders(
		<EditUserDialog {...props} />,
	);
	expect(screen.getByRole("alert")).toHaveTextContent(
		"Load them before saving",
	);
	expect(screen.getByRole("button", { name: "Save Changes" })).toBeDisabled();
	await user.click(screen.getByRole("button", { name: "Retry roles" }));
	expect(refetch).toHaveBeenCalledTimes(2);
	mockUserRoles.mockReturnValue({ data: { role_ids: [] }, refetch });
	rerender(<EditUserDialog {...props} />);
	expect(screen.getByRole("button", { name: "Save Changes" })).toBeEnabled();
});

it("does not repeat completed role removals after a partial save failure", async () => {
	mockRoles.mockReturnValue({
		data: [
			{ id: "r1", name: "Reviewer" },
			{ id: "r2", name: "Operator" },
		],
	});
	mockUserRoles.mockReturnValue({ data: { role_ids: ["r1", "r2"] } });
	mockRemoveMutate
		.mockResolvedValueOnce({})
		.mockRejectedValueOnce(new Error("Synthetic role removal failure"))
		.mockResolvedValueOnce({});
	const { user } = renderWithProviders(
		<EditUserDialog user={makeUser()} open onOpenChange={vi.fn()} />,
	);
	await user.click(
		screen.getByRole("button", { name: "Remove Reviewer role" }),
	);
	await user.click(
		screen.getByRole("button", { name: "Remove Operator role" }),
	);
	await user.click(screen.getByRole("button", { name: "Save Changes" }));
	expect(await screen.findByRole("alert")).toHaveTextContent(
		"Synthetic role removal failure",
	);
	await user.click(screen.getByRole("button", { name: "Save Changes" }));
	await waitFor(() => expect(mockRemoveMutate).toHaveBeenCalledTimes(3));
	expect(
		mockRemoveMutate.mock.calls.map(([args]) => args.params.path.role_id),
	).toEqual(["r1", "r2", "r2"]);
	expect(mockUpdateMutate).not.toHaveBeenCalled();
});
