import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";

const mockNavigate = vi.fn();
const mockUseAuth = vi.fn();
const mockUseForms = vi.fn();

vi.mock("react-router-dom", async () => {
	const actual =
		await vi.importActual<typeof import("react-router-dom")>(
			"react-router-dom",
		);
	return {
		...actual,
		useNavigate: () => mockNavigate,
	};
});

vi.mock("@/contexts/AuthContext", () => ({
	useAuth: () => mockUseAuth(),
}));

vi.mock("@/hooks/useForms", () => ({
	useForms: () => mockUseForms(),
}));

function makeForm(overrides: Record<string, unknown> = {}) {
	return {
		id: "form-1",
		name: "Onboarding",
		description: "Create a new client",
		organization_id: null,
		is_active: true,
		workflow_id: "workflow-1",
		form_schema: { fields: [{ name: "client_name" }] },
		missing_required_params: [],
		...overrides,
	};
}

beforeEach(() => {
	vi.clearAllMocks();
	mockUseAuth.mockReturnValue({ isPlatformAdmin: false });
	mockUseForms.mockReturnValue({
		data: [],
		isLoading: false,
		isError: false,
		isFetching: false,
		refetch: vi.fn(),
	});
});

async function renderPage() {
	const { ExecuteForms } = await import("./ExecuteForms");
	return renderWithProviders(<ExecuteForms />);
}

describe("ExecuteForms", () => {
	it("shows retry instead of a false empty state when the initial read fails", async () => {
		const refetch = vi.fn();
		mockUseForms.mockReturnValue({
			data: undefined,
			isLoading: false,
			isError: true,
			isFetching: false,
			error: new Error("offline"),
			refetch,
		});

		const { user } = await renderPage();

		expect(screen.getByRole("alert")).toHaveTextContent(
			"Could not load forms",
		);
		expect(
			screen.queryByText(/No active forms available/i),
		).not.toBeInTheDocument();

		await user.click(screen.getByRole("button", { name: "Retry loading" }));
		expect(refetch).toHaveBeenCalledOnce();
	});

	it("keeps cached active forms visible while refreshing and filters invalid forms for non-admins", async () => {
		const refetch = vi.fn();
		mockUseForms.mockReturnValue({
			data: [
				makeForm(),
				makeForm({
					id: "form-2",
					name: "Needs params",
					missing_required_params: ["workflow.step_id"],
				}),
				makeForm({
					id: "form-3",
					name: "Inactive",
					is_active: false,
				}),
			],
			isLoading: false,
			isError: true,
			isFetching: true,
			error: new Error("temporarily unavailable"),
			refetch,
		});

		const { user } = await renderPage();

		expect(screen.getByRole("alert")).toHaveTextContent(
			"Previously loaded forms are still shown.",
		);
		expect(screen.getByText("Onboarding")).toBeVisible();
		expect(screen.queryByText("Needs params")).not.toBeInTheDocument();
		expect(screen.queryByText("Inactive")).not.toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: "Retrying…" }),
		).toBeDisabled();

		await user.click(
			screen.getByRole("button", { name: /execute workflow/i }),
		);
		expect(mockNavigate).toHaveBeenCalledWith("/execute/form-1");
	});

	it("keeps admin-visible invalid forms readable on narrow cards", async () => {
		mockUseAuth.mockReturnValue({ isPlatformAdmin: true });
		const longName =
			"Very long onboarding form name that should wrap instead of truncating";
		const longWorkflowId = `workflow-${"a".repeat(80)}`;
		const longParam = `step_${"b".repeat(80)}`;
		mockUseForms.mockReturnValue({
			data: [
				makeForm({
					id: "form-4",
					name: longName,
					workflow_id: longWorkflowId,
					missing_required_params: [longParam],
				}),
			],
			isLoading: false,
			isError: false,
			isFetching: false,
			refetch: vi.fn(),
		});

		await renderPage();

		expect(screen.getByText(longName).closest("span")).not.toHaveClass(
			"truncate",
		);
		expect(screen.getByText(longWorkflowId).closest("p")).toHaveClass(
			"[overflow-wrap:anywhere]",
		);
		expect(screen.getByText(longParam).closest("span")).toHaveClass(
			"break-all",
		);
		expect(
			screen.getByRole("button", { name: /execute workflow/i }),
		).toBeDisabled();
	});
});
