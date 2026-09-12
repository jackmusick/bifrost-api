import { TableDetail } from "./TableDetail";
/**
 * Tests for TableDetail's solution-aware back-link. When the page is reached
 * from a Solution detail view (`?from=solution:{id}`) the back affordance
 * retargets to the Solution; otherwise it points at the tables list.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import userEvent from "@testing-library/user-event";
import { waitFor } from "@testing-library/react";
import { Routes, Route } from "react-router-dom";
import { renderWithProviders, screen } from "@/test-utils";

const mockUseTable = vi.fn();
const mockUseDocuments = vi.fn();
const mockUseDeleteDocument = vi.fn();

vi.mock("@/services/tables", () => ({
	useTable: (...a: unknown[]) => mockUseTable(...a),
	useDocuments: (...a: unknown[]) => mockUseDocuments(...a),
	useDeleteDocument: (...a: unknown[]) => mockUseDeleteDocument(...a),
}));

vi.mock("@/components/tables/DocumentDialog", () => ({
	DocumentDialog: () => null,
}));

vi.mock("@/components/tables/DocumentInspector", () => ({
	DocumentInspector: ({
		document,
		editing,
		onEdit,
		onClose,
	}: {
		document?: { id: string };
		editing: boolean;
		onEdit: () => void;
		onClose: () => void;
	}) => (
		<div>
			<span>
				{editing ? "Editing Record" : "Formatted Record"} {document?.id}
			</span>
			<button onClick={onEdit}>Edit Record</button>
			<button onClick={onClose}>Close Record</button>
		</div>
	),
}));

vi.mock("@/components/tables/TableFilterSidebar", () => ({
	TableFilterSidebar: () => null,
}));

const table = {
	id: "tbl-1",
	name: "Customers",
	description: "",
	organization_id: null,
	created_at: "2026-01-01T00:00:00Z",
};

beforeEach(() => {
	vi.clearAllMocks();
	mockUseTable.mockReturnValue({ data: table, isLoading: false });
	mockUseDocuments.mockReturnValue({
		data: { documents: [], total: 0 },
		isLoading: false,
		refetch: vi.fn(),
	});
	mockUseDeleteDocument.mockReturnValue({ mutateAsync: vi.fn() });
});

async function renderAtRoute(path: string) {
	return renderWithProviders(
		<Routes>
			<Route path="/tables/:tableId" element={<TableDetail />} />
		</Routes>,
		{ initialEntries: [path] },
	);
}

describe("TableDetail — solution back-nav", () => {
	it("retargets the back-link to the solution with ?from=solution:", async () => {
		await renderAtRoute("/tables/tbl-1?from=solution:s1");
		const back = screen.getByRole("link", { name: /back to solution/i });
		expect(back).toHaveAttribute("href", "/solutions/s1");
	});

	it("points the back-link at /tables without ?from", async () => {
		await renderAtRoute("/tables/tbl-1");
		const back = screen.getByRole("link", { name: /back to tables/i });
		expect(back).toHaveAttribute("href", "/tables");
	});
});

describe("TableDetail document navigation and recovery", () => {
	it("keeps pagination reachable when the current-page search has no matches", async () => {
		const user = userEvent.setup();
		mockUseDocuments.mockReturnValue({
			data: {
				documents: [
					{ id: "doc-1", data: { name: "Alpha" }, created_at: null },
				],
				total: 50,
			},
			isLoading: false,
			refetch: vi.fn(),
		});
		await renderAtRoute("/tables/tbl-1");
		await user.type(
			screen.getByRole("textbox", {
				name: "Search documents on this page",
			}),
			"missing",
		);
		await screen.findByText("No documents match on this page");
		await user.click(screen.getByRole("button", { name: "Next" }));
		expect(mockUseDocuments).toHaveBeenLastCalledWith(
			"tbl-1",
			expect.objectContaining({ offset: 25, limit: 25 }),
			{ preservePageData: true },
		);
		expect(
			screen.getByRole("textbox", {
				name: "Search documents on this page",
			}),
		).toHaveValue("missing");
	});

	it("keeps retained documents and paging controls mounted during a page fetch", async () => {
		mockUseDocuments.mockReturnValue({
			data: {
				documents: [
					{ id: "doc-1", data: { name: "Alpha" }, created_at: null },
				],
				total: 50,
			},
			isLoading: false,
			isFetching: true,
			refetch: vi.fn(),
		});

		await renderAtRoute("/tables/tbl-1");

		expect(
			screen.getByRole("region", { name: "Documents" }),
		).toHaveAttribute("aria-busy", "true");
		expect(screen.getAllByText("Alpha").length).toBeGreaterThan(0);
		expect(screen.getByLabelText("Loading page")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
	});

	it("distinguishes a failed query from an empty table and offers retry", async () => {
		const user = userEvent.setup();
		const refetch = vi.fn();
		mockUseDocuments.mockReturnValue({
			data: undefined,
			isLoading: false,
			isError: true,
			refetch,
		});
		await renderAtRoute("/tables/tbl-1");
		expect(screen.getByRole("alert")).toHaveTextContent(
			"Documents could not be loaded",
		);
		expect(screen.queryByText("No documents yet")).not.toBeInTheDocument();
		await user.click(
			screen.getByRole("button", { name: "Retry documents" }),
		);
		expect(refetch).toHaveBeenCalledOnce();
	});

	it("retains a failed deletion and retries the same document", async () => {
		const user = userEvent.setup();
		const mutateAsync = vi
			.fn()
			.mockRejectedValueOnce(new Error("failed"))
			.mockResolvedValueOnce(undefined);
		mockUseDeleteDocument.mockReturnValue({ mutateAsync });
		mockUseDocuments.mockReturnValue({
			data: {
				documents: [
					{ id: "doc-1", data: { name: "Alpha" }, created_at: null },
				],
				total: 1,
			},
			isLoading: false,
			refetch: vi.fn(),
		});
		await renderAtRoute("/tables/tbl-1");
		await user.click(
			screen.getAllByRole("button", {
				name: /^Document .* actions$/,
			})[0],
		);
		await user.click(screen.getByRole("menuitem", { name: "Delete" }));
		const { within } = await import("@testing-library/react");
		await user.click(
			within(screen.getByRole("alertdialog")).getByRole("button", {
				name: "Delete document",
			}),
		);
		expect(await screen.findByRole("alert")).toHaveTextContent(
			"Document could not be deleted",
		);
		await user.click(
			screen.getByRole("button", { name: "Retry deletion" }),
		);
		await waitFor(() =>
			expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument(),
		);
		expect(mutateAsync).toHaveBeenCalledTimes(2);
		expect(mutateAsync.mock.calls[1][0]).toEqual({
			params: { path: { table_id: "tbl-1", doc_id: "doc-1" } },
		});
	});
});

it("gives the initial loading and failed table states a page heading and retry", async () => {
	const retry = vi.fn();
	mockUseTable.mockReturnValue({
		data: undefined,
		isLoading: true,
		isFetching: true,
		isError: false,
		refetch: retry,
	});
	const view = await renderAtRoute("/tables/tbl-1?from=solution:s1");
	expect(
		screen.getByRole("heading", { level: 2, name: "Loading table…" }),
	).toBeInTheDocument();
	expect(
		screen.getByRole("link", { name: "Back to Solution" }),
	).toHaveAttribute("href", "/solutions/s1");
	view.unmount();
	mockUseTable.mockReturnValue({
		data: undefined,
		isLoading: false,
		isFetching: false,
		isError: true,
		refetch: retry,
	});
	const { user } = await renderAtRoute("/tables/tbl-1");
	expect(
		screen.getByRole("heading", {
			level: 2,
			name: "Table could not be loaded",
		}),
	).toBeInTheDocument();
	expect(
		screen.queryByRole("button", { name: "Add document" }),
	).not.toBeInTheDocument();
	await user.click(screen.getByRole("button", { name: "Retry table" }));
	expect(retry).toHaveBeenCalledOnce();
});

it("opens formatted records in the workspace and switches to editing without a modal", async () => {
	mockUseDocuments.mockReturnValue({
		data: {
			documents: [
				{ id: "doc-1", data: { name: "Alpha" }, created_at: null },
			],
			total: 1,
		},
		isLoading: false,
		refetch: vi.fn(),
	});
	const { user } = await renderAtRoute("/tables/tbl-1");
	await user.click(
		screen.getByRole("button", { name: "Open document doc-1" }),
	);
	expect(
		screen.getByRole("region", { name: "Document inspector" }),
	).toHaveTextContent("Formatted Record doc-1");
	expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
	await user.click(screen.getByRole("button", { name: "Edit Record" }));
	expect(
		screen.getByRole("region", { name: "Document inspector" }),
	).toHaveTextContent("Editing Record");
	await user.click(screen.getByRole("button", { name: "Close Record" }));
	await waitFor(() =>
		expect(
			screen.queryByRole("region", { name: "Document inspector" }),
		).not.toBeInTheDocument(),
	);
});
