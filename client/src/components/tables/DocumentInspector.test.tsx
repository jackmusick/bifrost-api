import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen, within } from "@/test-utils";
import type { DocumentPublic } from "@/services/tables";

const mockDocumentDialog = vi.fn(
	(props: {
		document: DocumentPublic | undefined;
		tableId: string;
		open: boolean;
		embedded?: boolean;
		onClose: () => void;
		onBusyChange?: (busy: boolean) => void;
	}) => (
		<div role="region" aria-label="Mock document editor">
			<button type="button" onClick={() => props.onBusyChange?.(true)}>
				Busy
			</button>
			<button type="button" onClick={props.onClose}>
				Close editor
			</button>
			<span>{props.embedded ? "embedded" : "modal"}</span>
			<span>{props.tableId}</span>
			<span>{props.document?.id ?? "new"}</span>
		</div>
	),
);

vi.mock("./DocumentDialog", () => ({
	DocumentDialog: (props: Parameters<typeof mockDocumentDialog>[0]) =>
		mockDocumentDialog(props),
}));

vi.mock("react-syntax-highlighter", () => ({
	Prism: ({
		children,
		...props
	}: {
		children: string;
		"aria-label"?: string;
	}) => <pre aria-label={props["aria-label"]}>{children}</pre>,
}));

vi.mock("sonner", () => ({
	toast: {
		success: vi.fn(),
		error: vi.fn(),
	},
}));

import { DocumentInspector } from "./DocumentInspector";

const doc = {
	id: "doc-1",
	table_id: "tbl-1",
	data: {
		name: "Acme",
		active: true,
		profile: { tier: "gold" },
	},
	created_at: "2026-04-20T12:00:00Z",
	updated_at: "2026-04-21T12:00:00Z",
	created_by: null,
	updated_by: null,
} satisfies DocumentPublic;

describe("DocumentInspector", () => {
	it("renders document data by default with copyable ID and collapsed metadata", () => {
		renderWithProviders(
			<DocumentInspector
				document={doc}
				tableId="tbl-1"
				editing={false}
				onEdit={vi.fn()}
				onClose={vi.fn()}
			/>,
		);

		expect(
			screen.getByRole("heading", { name: "Document" }),
		).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: "Copy Document ID" }),
		).toHaveTextContent("doc-1");
		expect(screen.getByText("Name")).toBeInTheDocument();
		expect(screen.getByText("Acme")).toBeInTheDocument();
		expect(screen.queryByText(/Apr/)).not.toBeInTheDocument();
	});

	it("shows explicit JSON and compact metadata without a row disclosure", async () => {
		const { user } = renderWithProviders(
			<DocumentInspector
				document={doc}
				tableId="tbl-1"
				editing={false}
				onEdit={vi.fn()}
				onClose={vi.fn()}
			/>,
		);

		await user.click(screen.getByRole("tab", { name: /json/i }));
		expect(screen.getByLabelText("Document JSON")).toHaveTextContent(
			'"name": "Acme"',
		);
		expect(
			screen.queryByRole("button", { name: /view full json/i }),
		).not.toBeInTheDocument();

		await user.click(screen.getByRole("button", { name: "Metadata" }));
		expect(screen.getByText("created_at:")).toBeInTheDocument();
		expect(screen.getByText("updated_at:")).toBeInTheDocument();
	});

	it("calls the attached inspector actions from the fixed footer and header", async () => {
		const onEdit = vi.fn();
		const onClose = vi.fn();
		const onDelete = vi.fn();
		const { user } = renderWithProviders(
			<DocumentInspector
				document={doc}
				tableId="tbl-1"
				editing={false}
				onEdit={onEdit}
				onClose={onClose}
				onDelete={onDelete}
			/>,
		);

		await user.click(
			screen.getByRole("button", { name: "Close document inspector" }),
		);
		await user.click(screen.getByRole("button", { name: "Edit" }));
		await user.click(screen.getByRole("button", { name: "Delete" }));

		expect(onClose).toHaveBeenCalledOnce();
		expect(onEdit).toHaveBeenCalledOnce();
		expect(onDelete).toHaveBeenCalledOnce();

		const footer = screen.getByRole("button", {
			name: "Edit",
		}).parentElement;
		expect(footer).toHaveClass("shrink-0", "border-t");
	});

	it("delegates editing to the embedded DocumentDialog and forwards busy changes", async () => {
		const onClose = vi.fn();
		const onBusyChange = vi.fn();
		const { user } = renderWithProviders(
			<DocumentInspector
				document={doc}
				tableId="tbl-1"
				editing
				onEdit={vi.fn()}
				onClose={onClose}
				onBusyChange={onBusyChange}
			/>,
		);

		const editor = screen.getByRole("region", {
			name: "Mock document editor",
		});
		expect(within(editor).getByText("embedded")).toBeInTheDocument();
		expect(within(editor).getByText("tbl-1")).toBeInTheDocument();
		expect(within(editor).getByText("doc-1")).toBeInTheDocument();
		expect(mockDocumentDialog).toHaveBeenLastCalledWith(
			expect.objectContaining({
				document: doc,
				tableId: "tbl-1",
				open: true,
				embedded: true,
				onClose,
				onBusyChange,
			}),
		);

		await user.click(screen.getByRole("button", { name: "Busy" }));
		await user.click(screen.getByRole("button", { name: "Close editor" }));
		expect(onBusyChange).toHaveBeenCalledWith(true);
		expect(onClose).toHaveBeenCalledOnce();
	});
});
