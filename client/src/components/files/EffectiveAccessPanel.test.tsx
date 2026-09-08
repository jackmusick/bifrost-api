import { type ComponentProps } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/services/filePolicies", () => ({
	effectiveAccess: vi.fn(),
}));
vi.mock("@/components/solutions/SolutionManagedBadge", () => ({
	SolutionManagedBadge: () => (
		<span data-testid="solution-managed-badge">Managed</span>
	),
}));
import { effectiveAccess } from "@/services/filePolicies";
import { EffectiveAccessPanel } from "./EffectiveAccessPanel";

describe("EffectiveAccessPanel", () => {
	beforeEach(() => vi.mocked(effectiveAccess).mockReset());

	function renderPanel(props: ComponentProps<typeof EffectiveAccessPanel>) {
		const queryClient = new QueryClient({
			defaultOptions: {
				queries: {
					retry: false,
				},
			},
		});
		return {
			...render(
				<QueryClientProvider client={queryClient}>
					<EffectiveAccessPanel {...props} />
				</QueryClientProvider>,
			),
			queryClient,
		};
	}

	it("renders the resolved cascade with the longest-prefix one winning", async () => {
		vi.mocked(effectiveAccess).mockResolvedValue([
			{
				id: "2",
				location: "gallery",
				path: "team/",
				policies: {
					policies: [{ name: "team-rule", actions: ["read"] }],
				},
			},
			{
				id: "1",
				location: "gallery",
				path: "",
				policies: {
					policies: [
						{ name: "root-rule", actions: ["read", "list"] },
					],
				},
			},
		]);
		renderPanel({
			location: "gallery",
			scope: null,
			path: "team/pic.png",
			onOpenTest: vi.fn(),
			onManagePolicy: vi.fn(),
		});
		await waitFor(() =>
			expect(screen.getByText("team-rule")).toBeInTheDocument(),
		);
		expect(screen.getByText("root-rule")).toBeInTheDocument();
		expect(screen.getByText("winning")).toBeInTheDocument();
	});

	it("refreshes when the target identity changes", async () => {
		vi.mocked(effectiveAccess)
			.mockResolvedValueOnce([
				{
					id: "1",
					location: "gallery",
					path: "team/a/",
					policies: {
						policies: [{ name: "alpha-rule", actions: ["read"] }],
					},
				},
			])
			.mockResolvedValueOnce([
				{
					id: "2",
					location: "gallery",
					path: "team/b/",
					policies: {
						policies: [{ name: "beta-rule", actions: ["write"] }],
					},
				},
			]);
		const { rerender, queryClient } = renderPanel({
			location: "gallery",
			scope: null,
			path: "team/a/file.txt",
			onOpenTest: vi.fn(),
			onManagePolicy: vi.fn(),
		});
		await waitFor(() =>
			expect(screen.getByText("alpha-rule")).toBeInTheDocument(),
		);
		rerender(
			<QueryClientProvider client={queryClient}>
				<EffectiveAccessPanel
					location="gallery"
					scope={null}
					path="team/b/file.txt"
					onOpenTest={vi.fn()}
					onManagePolicy={vi.fn()}
				/>
			</QueryClientProvider>,
		);
		await waitFor(() =>
			expect(screen.getByText("beta-rule")).toBeInTheDocument(),
		);
		expect(screen.queryByText("alpha-rule")).not.toBeInTheDocument();
	});

	it("retries a failed access lookup", async () => {
		vi.mocked(effectiveAccess)
			.mockRejectedValueOnce(new Error("lookup failed"))
			.mockResolvedValueOnce([
				{
					id: "3",
					location: "gallery",
					path: "team/c/",
					policies: {
						policies: [
							{ name: "recovered-rule", actions: ["read"] },
						],
					},
				},
			]);
		renderPanel({
			location: "gallery",
			scope: null,
			path: "team/c/file.txt",
			onOpenTest: vi.fn(),
			onManagePolicy: vi.fn(),
		});
		expect(await screen.findByRole("alert")).toHaveTextContent(
			"Couldn’t resolve access",
		);
		fireEvent.click(screen.getByRole("button", { name: /retry access/i }));
		await waitFor(() =>
			expect(screen.getByText("recovered-rule")).toBeInTheDocument(),
		);
	});

	it("fires onOpenTest when Test access is clicked", async () => {
		vi.mocked(effectiveAccess).mockResolvedValue([]);
		const onOpenTest = vi.fn();
		renderPanel({
			location: "gallery",
			scope: null,
			path: "pic.png",
			onOpenTest,
			onManagePolicy: vi.fn(),
		});
		fireEvent.click(screen.getByRole("button", { name: /test access/i }));
		expect(onOpenTest).toHaveBeenCalled();
	});

	it("hides policy management in read-only solution file scope", async () => {
		vi.mocked(effectiveAccess).mockResolvedValue([]);
		const onManagePolicy = vi.fn();
		renderPanel({
			location: "reports",
			scope: "sol-1",
			path: "demo/readme.txt",
			readOnly: true,
			managedBySolution: true,
			solutionId: "sol-1",
			onOpenTest: vi.fn(),
			onManagePolicy,
		});

		expect(
			screen.queryByRole("button", { name: /manage policy/i }),
		).not.toBeInTheDocument();
		expect(
			screen.getByTestId("solution-managed-badge"),
		).toBeInTheDocument();
		expect(onManagePolicy).not.toHaveBeenCalled();
	});
});
