/**
 * Component tests for DocumentDialog.
 *
 * Monaco is huge and can't run in happy-dom, so we stub @monaco-editor/react
 * to a plain textarea wired to value/onChange. That lets us exercise the real
 * submit / validation behaviour without a browser.
 *
 * Covers:
 * - create-mode: valid JSON → insertDocument with parsed data
 * - edit-mode: pre-fills from document.data → updateDocument with doc_id
 * - invalid JSON: shows error alert, Save button is disabled
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderWithProviders, screen, waitFor, fireEvent } from "@/test-utils";

const mockInsertMutate = vi.fn();
const mockUpdateMutate = vi.fn();

vi.mock("@/services/tables", () => ({
	useInsertDocument: () => ({
		mutateAsync: mockInsertMutate,
		isPending: false,
	}),
	useUpdateDocument: () => ({
		mutateAsync: mockUpdateMutate,
		isPending: false,
	}),
}));

vi.mock("@/contexts/ThemeContext", () => ({
	useTheme: () => ({ theme: "light" }),
}));

// Monaco: stub to a textarea so we can drive value changes from tests.
vi.mock("@monaco-editor/react", () => ({
	default: ({
		value,
		onChange,
		options,
	}: {
		value?: string;
		onChange?: (v: string | undefined) => void;
		options?: { readOnly?: boolean };
	}) => (
		<textarea
			aria-label="document-json"
			readOnly={options?.readOnly}
			value={value ?? ""}
			onChange={(e) => onChange?.(e.target.value)}
		/>
	),
}));

import { DocumentDialog } from "./DocumentDialog";

beforeEach(() => {
	mockInsertMutate.mockReset();
	mockInsertMutate.mockResolvedValue({});
	mockUpdateMutate.mockReset();
	mockUpdateMutate.mockResolvedValue({});
});

describe("DocumentDialog — create mode", () => {
	it("parses the JSON and calls insertDocument with the table_id", async () => {
		const onClose = vi.fn();
		const { user } = renderWithProviders(
			<DocumentDialog tableId="tbl-1" open={true} onClose={onClose} />,
		);

		const editor = screen.getByLabelText(/document-json/i);
		fireEvent.change(editor, {
			target: { value: '{"foo": "bar"}' },
		});

		await user.click(screen.getByRole("button", { name: /^create$/i }));

		await waitFor(() => expect(mockInsertMutate).toHaveBeenCalled());
		expect(mockInsertMutate.mock.calls[0]![0]).toEqual({
			params: { path: { table_id: "tbl-1" } },
			body: { data: { foo: "bar" }, upsert: false },
		});
		expect(onClose).toHaveBeenCalled();
	});
});

describe("DocumentDialog — edit mode", () => {
	it("pre-fills from document.data and calls updateDocument with doc_id", async () => {
		const onClose = vi.fn();
		const doc = {
			id: "doc-1",
			data: { hello: "world" },
			created_at: "2026-04-20T00:00:00Z",
			updated_at: "2026-04-20T00:00:00Z",
		};
		const { user } = renderWithProviders(
			<DocumentDialog
				document={
					doc as unknown as Parameters<
						typeof DocumentDialog
					>[0]["document"]
				}
				tableId="tbl-1"
				open={true}
				onClose={onClose}
			/>,
		);

		const editor = screen.getByLabelText(
			/document-json/i,
		) as HTMLTextAreaElement;
		expect(editor.value).toContain('"hello": "world"');

		await user.click(screen.getByRole("button", { name: /^update$/i }));

		await waitFor(() => expect(mockUpdateMutate).toHaveBeenCalled());
		expect(mockUpdateMutate.mock.calls[0]![0]).toEqual({
			params: { path: { table_id: "tbl-1", doc_id: "doc-1" } },
			body: { data: { hello: "world" } },
		});
		expect(onClose).toHaveBeenCalled();
	});
});

describe("DocumentDialog — invalid JSON", () => {
	it("shows an error alert and disables the save button on invalid JSON", () => {
		renderWithProviders(
			<DocumentDialog tableId="tbl-1" open={true} onClose={vi.fn()} />,
		);

		const editor = screen.getByLabelText(/document-json/i);
		fireEvent.change(editor, { target: { value: "{not valid" } });

		expect(screen.getByRole("alert")).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: /^create$/i }),
		).toBeDisabled();
	});
});

it.each(["", "[]", "null", "42", '"text"'])(
	"rejects document data outside the object contract: %s",
	async (value) => {
		const { user } = renderWithProviders(
			<DocumentDialog tableId="tbl-1" open onClose={vi.fn()} />,
		);
		fireEvent.change(screen.getByLabelText("document-json"), {
			target: { value },
		});
		expect(screen.getByRole("button", { name: "Create" })).toBeDisabled();
		expect(screen.getByRole("alert")).toBeInTheDocument();
		await user.click(screen.getByRole("button", { name: "Create" }));
		expect(mockInsertMutate).not.toHaveBeenCalled();
	},
);

it("guards the pending session and retains its draft after failure for retry", async () => {
	let reject!: (error: Error) => void;
	mockInsertMutate.mockImplementationOnce(
		() =>
			new Promise((_, fail) => {
				reject = fail;
			}),
	);
	const onClose = vi.fn();
	const { user } = renderWithProviders(
		<DocumentDialog tableId="tbl-1" open onClose={onClose} />,
	);
	const editor = screen.getByLabelText("document-json");
	fireEvent.change(editor, {
		target: { value: '{"name":"Keep this draft"}' },
	});
	await user.click(screen.getByRole("button", { name: "Create" }));
	expect(editor).toHaveAttribute("readonly");
	expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
	expect(screen.getByRole("button", { name: "Format" })).toBeDisabled();
	await user.keyboard("{Escape}");
	expect(onClose).not.toHaveBeenCalled();
	reject(new Error("Synthetic failure"));
	await screen.findByText(/Document could not be saved/);
	expect(editor).toHaveValue('{"name":"Keep this draft"}');
	await user.click(screen.getByRole("button", { name: "Retry save" }));
	await waitFor(() => expect(onClose).toHaveBeenCalledOnce());
	expect(mockInsertMutate.mock.calls[1][0]).toEqual(
		mockInsertMutate.mock.calls[0][0],
	);
});

it("renders as an embedded editor and reports pending state to the parent", async () => {
	let resolveSave!: (value: unknown) => void;
	mockInsertMutate.mockImplementationOnce(
		() =>
			new Promise((resolve) => {
				resolveSave = resolve;
			}),
	);
	const onClose = vi.fn();
	const onBusyChange = vi.fn();
	const { user } = renderWithProviders(
		<DocumentDialog
			tableId="tbl-1"
			open
			onClose={onClose}
			embedded
			onBusyChange={onBusyChange}
		/>,
	);

	expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
	expect(
		screen.getByRole("region", { name: "Create Document" }),
	).toBeInTheDocument();

	fireEvent.change(screen.getByLabelText("document-json"), {
		target: { value: '{"name":"Inline"}' },
	});
	await user.click(screen.getByRole("button", { name: "Create" }));
	expect(onBusyChange).toHaveBeenLastCalledWith(true);
	expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
	await user.click(
		screen.getByRole("button", { name: "Close document editor" }),
	);
	expect(onClose).not.toHaveBeenCalled();

	resolveSave({});
	await waitFor(() => expect(onBusyChange).toHaveBeenLastCalledWith(false));
	expect(onClose).toHaveBeenCalledOnce();
});
