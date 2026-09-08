import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen, waitFor } from "@/test-utils";

const mockUseMediaQuery = vi.fn(() => false);

vi.mock("@/hooks/useMediaQuery", () => ({
	useMediaQuery: () => mockUseMediaQuery(),
}));

vi.mock("@/services/filePolicies", () => ({
	listFilePolicies: vi.fn(),
}));

import {
	listFilePolicies,
	type FilePolicyListResponse,
} from "@/services/filePolicies";
import { PoliciesView } from "./PoliciesView";

function deferred<T>() {
	let resolve!: (value: T) => void;
	const promise = new Promise<T>((res) => {
		resolve = res;
	});
	return { promise, resolve };
}

describe("PoliciesView", () => {
	beforeEach(() => {
		mockUseMediaQuery.mockReturnValue(false);
		vi.mocked(listFilePolicies).mockReset();
	});

	it("renders mobile policy cards below 1024px with wrapped rules and 44px actions", async () => {
		mockUseMediaQuery.mockReturnValue(true);
		vi.mocked(listFilePolicies).mockResolvedValue({
			policies: [
				{
					id: "p1",
					location: "gallery",
					path: "",
					organizationId: null,
					policies: {
						policies: [
							{
								name: "admin_bypass",
								actions: ["read"],
							},
							{
								$ref: "rules.super_long_rule_name_that_should_wrap_cleanly_in_the_badge",
							},
						],
					},
				},
				{
					id: "p2",
					location: "reports",
					path: "q1/",
					organizationId: null,
					policies: { policies: [] },
				},
			],
		});

		const onEdit = vi.fn();
		const onDelete = vi.fn();
		const { user } = renderWithProviders(
			<PoliciesView
				scope={null}
				refreshKey={0}
				onEdit={onEdit}
				onDelete={onDelete}
			/>,
		);

		expect(await screen.findByText("gallery")).toBeInTheDocument();
		expect(screen.getByText("/")).toBeInTheDocument();
		expect(screen.getByText("reports")).toBeInTheDocument();
		expect(screen.getByText("/q1/")).toBeInTheDocument();
		expect(screen.getByText("admin_bypass")).toBeInTheDocument();
		expect(
			screen.getByText(
				/rules\.super_long_rule_name_that_should_wrap_cleanly_in_the_badge/i,
			),
		).toBeInTheDocument();
		expect(screen.queryByRole("table")).not.toBeInTheDocument();

		const editButton = screen.getByRole("button", {
			name: /edit policy for gallery\//i,
		});
		expect(editButton).toHaveClass("min-h-11");
		await user.click(editButton);
		expect(onEdit).toHaveBeenCalledWith(
			expect.objectContaining({ location: "gallery", path: "" }),
		);

		await user.click(
			screen.getByRole("button", {
				name: /policy gallery\/ actions/i,
			}),
		);
		await user.click(screen.getByRole("menuitem", { name: "Delete" }));
		expect(onDelete).toHaveBeenCalledWith(
			expect.objectContaining({ location: "gallery", path: "" }),
		);
	});

	it("renders the desktop table and keeps the identity column readable", async () => {
		mockUseMediaQuery.mockReturnValue(false);
		vi.mocked(listFilePolicies).mockResolvedValue({
			policies: [
				{
					id: "p1",
					location: "reports",
					path: "q1/",
					organizationId: null,
					policies: {
						policies: [
							{ name: "team_access", actions: ["read", "list"] },
						],
					},
				},
			],
		});

		renderWithProviders(
			<PoliciesView
				scope={null}
				refreshKey={0}
				onEdit={vi.fn()}
				onDelete={vi.fn()}
			/>,
		);

		expect(await screen.findByRole("table")).toBeInTheDocument();
		expect(screen.getByText("reports")).toBeInTheDocument();
		expect(screen.getByText("/q1/")).toBeInTheDocument();
		expect(screen.getByText("team_access")).toBeInTheDocument();
	});

	it("shows retryable loading and error states without inventing empty results", async () => {
		vi.mocked(listFilePolicies)
			.mockRejectedValueOnce(new Error("Unavailable"))
			.mockResolvedValueOnce({ policies: [] });

		const { user } = renderWithProviders(
			<PoliciesView
				scope={null}
				refreshKey={0}
				onEdit={vi.fn()}
				onDelete={vi.fn()}
			/>,
		);

		expect(await screen.findByRole("alert")).toHaveTextContent(
			/File policies could not be loaded/i,
		);
		expect(
			screen.queryByText(/no policies in this scope yet/i),
		).not.toBeInTheDocument();

		await user.click(
			screen.getByRole("button", { name: /retry policies/i }),
		);

		await waitFor(() =>
			expect(
				screen.getByText(/no policies in this scope yet/i),
			).toBeInTheDocument(),
		);
	});

	it("drops stale scope records while a new scope is loading", async () => {
		const nextScope = deferred<FilePolicyListResponse>();

		vi.mocked(listFilePolicies)
			.mockResolvedValueOnce({
				policies: [
					{
						id: "p1",
						location: "gallery",
						path: "",
						organizationId: null,
						policies: {
							policies: [
								{ name: "allow_gallery", actions: ["read"] },
							],
						},
					},
				],
			})
			.mockImplementationOnce(() => nextScope.promise);

		const { rerender } = renderWithProviders(
			<PoliciesView
				scope={null}
				refreshKey={0}
				onEdit={vi.fn()}
				onDelete={vi.fn()}
			/>,
		);

		expect(await screen.findByText("gallery")).toBeInTheDocument();

		rerender(
			<PoliciesView
				scope="org-2"
				refreshKey={0}
				onEdit={vi.fn()}
				onDelete={vi.fn()}
			/>,
		);

		expect(screen.queryByText("gallery")).not.toBeInTheDocument();
		expect(screen.getByText(/loading/i)).toBeInTheDocument();

		nextScope.resolve({
			policies: [
				{
					id: "p2",
					location: "reports",
					path: "q1/",
					organizationId: "org-2",
					policies: {
						policies: [{ name: "org_scope", actions: ["read"] }],
					},
				},
			],
		});

		await waitFor(() =>
			expect(screen.getByText("reports")).toBeInTheDocument(),
		);
		expect(screen.getByText("/q1/")).toBeInTheDocument();
	});
});
