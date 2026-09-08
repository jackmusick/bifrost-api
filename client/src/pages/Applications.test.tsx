/**
 * Tests for the Applications page — focused on the SolutionManagedBadge
 * affordance: managed apps show the shared admin-only badge and hide
 * Edit/Delete controls; non-managed apps keep their management controls.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderWithProviders, screen, within } from "@/test-utils";

const mockUseApplications = vi.fn();
const mockUseDeleteApplication = vi.fn();
vi.mock("@/lib/detail-route-loaders", () => ({
	prefetchApplicationDetail: vi.fn(),
}));
vi.mock("@/hooks/useMediaQuery", () => ({ useIsDesktop: () => true }));

vi.mock("@/hooks/useApplications", () => ({
	useApplications: () => mockUseApplications(),
	useDeleteApplication: () => mockUseDeleteApplication(),
}));

const mockUseAuth = vi.fn();
vi.mock("@/contexts/AuthContext", () => ({
	useAuth: () => mockUseAuth(),
}));

vi.mock("@/hooks/useOrganizations", () => ({
	useOrganizations: () => ({ data: [] }),
}));

// Keep the icon contract observable without loading image resources in happy-dom.
vi.mock("@/components/EntityLogo", () => ({
	EntityLogo: ({ logo }: { logo?: string | null }) => (
		<span data-testid="entity-logo" data-logo={logo ?? ""} />
	),
}));
vi.mock("@/components/app-builder/AppInfoDialog", () => ({
	AppInfoDialog: () => null,
}));
vi.mock("@/components/search/SearchBox", () => ({ SearchBox: () => null }));
vi.mock("@/components/forms/OrganizationSelect", () => ({
	OrganizationSelect: () => null,
}));

function makeApp(overrides: Partial<Record<string, unknown>> = {}) {
	return {
		id: "app-1",
		name: "Live Dash",
		slug: "live-dash",
		description: "A dashboard",
		organization_id: null,
		is_published: true,
		has_unpublished_changes: false,
		is_solution_managed: false,
		solution_id: null,
		logo_url: "/api/applications/app-1/logo",
		app_model: "legacy",
		...overrides,
	};
}

beforeEach(() => {
	mockUseAuth.mockReturnValue({ isPlatformAdmin: true });
	mockUseDeleteApplication.mockReturnValue({
		mutateAsync: vi.fn(),
		isPending: false,
	});
	mockUseApplications.mockReturnValue({
		data: { applications: [] },
		isLoading: false,
		refetch: vi.fn(),
	});
});

async function renderPage() {
	const { Applications } = await import("./Applications");
	return renderWithProviders(<Applications />);
}

describe("Applications — app launch behavior", () => {
	it("shows a loading indicator while the list loads", async () => {
		mockUseApplications.mockReturnValue({
			data: undefined,
			isLoading: true,
			refetch: vi.fn(),
		});
		await renderPage();
		expect(
			screen.getByRole("status", { name: /loading applications/i }),
		).toBeInTheDocument();
	});

	it("does not expose the deprecated create code application action", async () => {
		await renderPage();
		expect(
			screen.queryByTitle(/create application/i),
		).not.toBeInTheDocument();
	});

	it("opens v2 apps directly without showing an Open Published hover action", async () => {
		mockUseApplications.mockReturnValue({
			data: {
				applications: [
					makeApp({
						app_model: "standalone_v2",
						is_published: true,
					}),
				],
			},
			isLoading: false,
			refetch: vi.fn(),
		});
		await renderPage();
		expect(
			screen.getByRole("button", { name: "Live Dash" }),
		).toBeInTheDocument();
		expect(screen.queryByText(/open published/i)).not.toBeInTheDocument();
	});

	it("shows an undeployed v2 App without an in-platform code editor", async () => {
		mockUseApplications.mockReturnValue({
			data: {
				applications: [
					makeApp({
						app_model: "standalone_v2",
						is_published: false,
					}),
				],
			},
			isLoading: false,
			refetch: vi.fn(),
		});
		await renderPage();
		expect(screen.getByText("Not deployed")).toBeInTheDocument();
		expect(
			screen.queryByRole("button", { name: /code editor/i }),
		).not.toBeInTheDocument();
	});
});

describe("Applications — solution-managed badge (grid view)", () => {
	it("shows the badge and hides Edit/Code on a managed app", async () => {
		mockUseApplications.mockReturnValue({
			data: {
				applications: [
					makeApp({
						id: "m",
						name: "Managed App",
						is_solution_managed: true,
						solution_id: "s1",
					}),
				],
			},
			isLoading: false,
			refetch: vi.fn(),
		});
		await renderPage();
		const badge = screen.getByTestId("solution-managed-badge");
		expect(badge).toHaveAttribute("href", "/solutions/s1");
		// Managed apps must not expose management menus.
		expect(
			screen.queryByRole("button", { name: "Managed App actions" }),
		).not.toBeInTheDocument();
		expect(
			screen.queryByRole("button", { name: /delete application/i }),
		).not.toBeInTheDocument();
		expect(
			screen.queryByRole("button", { name: /settings/i }),
		).not.toBeInTheDocument();
		expect(
			screen.queryByRole("button", { name: /code editor/i }),
		).not.toBeInTheDocument();
	});

	it("shows Edit/Code controls and no badge on a non-managed app", async () => {
		mockUseApplications.mockReturnValue({
			data: { applications: [makeApp()] },
			isLoading: false,
			refetch: vi.fn(),
		});
		const { user } = await renderPage();
		await user.click(
			screen.getByRole("button", { name: "Live Dash actions" }),
		);
		expect(
			screen.queryByTestId("solution-managed-badge"),
		).not.toBeInTheDocument();
		expect(
			screen.getByRole("menuitem", { name: /settings/i }),
		).toBeInTheDocument();
		expect(
			screen.getByRole("menuitem", { name: /code editor/i }),
		).toBeInTheDocument();
	});
});

describe("Applications — solution-managed badge (table view)", () => {
	async function renderTable(apps: ReturnType<typeof makeApp>[]) {
		mockUseApplications.mockReturnValue({
			data: { applications: apps },
			isLoading: false,
			refetch: vi.fn(),
		});
		const { user } = await renderPage();
		await user.click(screen.getByLabelText(/table view/i));
		return user;
	}

	it("shows the badge and hides Delete on a managed app row", async () => {
		await renderTable([
			makeApp({
				id: "m",
				name: "Managed App",
				is_solution_managed: true,
				solution_id: "s1",
			}),
		]);
		const table = document.querySelector("table")!;
		const badge = within(table).getByTestId("solution-managed-badge");
		expect(badge).toHaveAttribute("href", "/solutions/s1");
		expect(
			within(table).queryByRole("button", { name: /delete/i }),
		).not.toBeInTheDocument();
	});

	it("shows Delete and no badge on a non-managed app row", async () => {
		const user = await renderTable([makeApp()]);
		await user.click(
			screen.getByRole("button", { name: "Live Dash actions" }),
		);
		const table = document.querySelector("table")!;
		expect(within(table).getByTestId("entity-logo")).toHaveAttribute(
			"data-logo",
			"/api/applications/app-1/logo",
		);
		expect(
			within(table).queryByTestId("solution-managed-badge"),
		).not.toBeInTheDocument();
		expect(
			screen.getByRole("menuitem", { name: "Delete" }),
		).toBeInTheDocument();
	});
});

it("distinguishes a failed initial lookup from an empty list and retries", async () => {
	const refetch = vi.fn();
	mockUseApplications.mockReturnValue({
		data: undefined,
		isLoading: false,
		isError: true,
		isFetching: false,
		refetch,
	});
	const { user } = await renderPage();
	expect(screen.getByRole("alert")).toHaveTextContent("Couldn't load");
	expect(screen.queryByText(/No .* found/i)).not.toBeInTheDocument();
	await user.click(screen.getByRole("button", { name: "Retry loading" }));
	expect(refetch).toHaveBeenCalledTimes(1);
});

it("opens card deletion without launching the app", async () => {
	mockUseApplications.mockReturnValue({
		data: { applications: [makeApp()] },
		isLoading: false,
		refetch: vi.fn(),
	});
	const { user } = await renderPage();
	screen.getByRole("button", { name: "Live Dash actions" }).focus();
	await user.keyboard("{Enter}");
	screen.getByRole("menuitem", { name: "Delete" }).focus();
	await user.keyboard("{Enter}");
	expect(screen.getByRole("alertdialog")).toHaveTextContent("Live Dash");
});
