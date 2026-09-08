import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, screen, waitFor } from "@/test-utils";
import { renderWithProviders } from "@/test-utils";

const mockImportEntities = vi.hoisted(() => vi.fn());
const mockImportAll = vi.hoisted(() => vi.fn());
const mockUseOrganizations = vi.hoisted(() => vi.fn());
const mockToast = vi.hoisted(() => ({
	success: vi.fn(),
	error: vi.fn(),
}));

vi.mock("@/services/exportImport", () => ({
	importEntities: (...args: unknown[]) => mockImportEntities(...args),
	importAll: (...args: unknown[]) => mockImportAll(...args),
}));

vi.mock("@/hooks/useOrganizations", () => ({
	useOrganizations: (...args: unknown[]) => mockUseOrganizations(...args),
}));

vi.mock("sonner", () => ({
	toast: mockToast,
}));

import { ImportDialog } from "./ImportDialog";

function renderDialog(entityType: "tables" | "all" = "tables") {
	const onOpenChange = vi.fn();
	const rendered = renderWithProviders(
		<ImportDialog
			open
			onOpenChange={onOpenChange}
			entityType={entityType}
			onImportComplete={vi.fn()}
		/>,
	);
	return { ...rendered, onOpenChange };
}

function getFileInput() {
	const zone = screen.getByRole("button", { name: /choose import file/i });
	const input = zone.querySelector('input[type="file"]');
	if (!input) {
		throw new Error("import file input not found");
	}
	return input as HTMLInputElement;
}

beforeEach(() => {
	mockImportEntities.mockReset();
	mockImportAll.mockReset();
	mockUseOrganizations.mockReset();
	mockToast.success.mockReset();
	mockToast.error.mockReset();
	mockUseOrganizations.mockReturnValue({ data: [] });
});

afterEach(() => {
	vi.useRealTimers();
});

describe("ImportDialog", () => {
	it("parses a JSON export, supports keyboard selection, and imports the filtered payload", async () => {
		const { user } = renderDialog("tables");
		const file = new File(
			[
				JSON.stringify({
					entity_type: "tables",
					item_count: 2,
					items: [
						{
							name: "alpha",
							documents: [{ id: "doc-1" }],
						},
						{
							name: "beta",
							documents: [{ id: "doc-2" }, { id: "doc-3" }],
						},
					],
				}),
			],
			"tables.json",
			{ type: "application/json" },
		);

		fireEvent.change(getFileInput(), {
			target: { files: [file] },
		});

		await screen.findByText("alpha");
		await user.click(screen.getByRole("checkbox", { name: /beta/i }));

		mockImportEntities.mockResolvedValueOnce({
			entity_type: "tables",
			created: 1,
			updated: 0,
			skipped: 0,
			errors: 0,
			warnings: [],
		});

		await user.click(screen.getByRole("button", { name: /import \(1\)/i }));

		await waitFor(() => {
			expect(mockImportEntities).toHaveBeenCalledTimes(1);
		});

		const [, filteredFile, options] = mockImportEntities.mock.calls[0] as [
			string,
			File,
			{
				replaceExisting: boolean;
				sourceSecretKey?: string;
				targetOrganizationId?: string | null;
			},
		];

		expect(options).toMatchObject({
			replaceExisting: true,
			sourceSecretKey: undefined,
			targetOrganizationId: undefined,
		});

		const filteredJson = JSON.parse(await filteredFile.text()) as {
			items: Array<{ name: string }>;
		};
		expect(filteredJson.items).toHaveLength(1);
		expect(filteredJson.items[0].name).toBe("alpha");
		expect(mockToast.success).toHaveBeenCalledWith("Import completed");
		expect(
			await screen.findByRole("button", { name: /done/i }),
		).toBeVisible();
	});

	it("passes ZIP imports through to importAll", async () => {
		const { user } = renderDialog("all");
		const file = new File(["zip-bytes"], "backup.zip", {
			type: "application/zip",
		});

		fireEvent.change(getFileInput(), {
			target: { files: [file] },
		});

		mockImportAll.mockResolvedValueOnce({
			entity_type: "all",
			created: 1,
			updated: 0,
			skipped: 0,
			errors: 0,
			warnings: [],
		});

		await user.click(screen.getByRole("button", { name: /^import$/i }));

		await waitFor(() => {
			expect(mockImportAll).toHaveBeenCalledTimes(1);
		});

		expect(mockImportAll).toHaveBeenCalledWith(
			file,
			expect.objectContaining({
				replaceExisting: true,
			}),
		);
		expect(mockToast.success).toHaveBeenCalledWith("Import completed");
		expect(
			await screen.findByRole("button", { name: /done/i }),
		).toBeVisible();
	});

	it("shows parse errors for invalid JSON files", async () => {
		renderDialog("tables");

		const file = new File(["not-json"], "broken.json", {
			type: "application/json",
		});
		fireEvent.change(getFileInput(), {
			target: { files: [file] },
		});

		const alert = await screen.findByRole("alert");
		expect(alert).toHaveTextContent(/failed to parse json file/i);
		expect(
			screen.getByRole("button", { name: /^import$/i }),
		).toBeDisabled();
	});

	it("keeps the dialog open after an import failure and allows retry", async () => {
		const { user, onOpenChange } = renderDialog("tables");
		const file = new File(
			[
				JSON.stringify({
					entity_type: "tables",
					item_count: 1,
					items: [
						{
							name: "alpha",
							documents: [{ id: "doc-1" }],
						},
					],
				}),
			],
			"tables.json",
			{ type: "application/json" },
		);

		fireEvent.change(getFileInput(), {
			target: { files: [file] },
		});

		await screen.findByText("alpha");

		let rejectFirst!: (reason?: unknown) => void;
		const firstAttempt = new Promise<never>((_resolve, reject) => {
			rejectFirst = reject;
		});
		mockImportEntities
			.mockReturnValueOnce(firstAttempt)
			.mockResolvedValueOnce({
				entity_type: "tables",
				created: 1,
				updated: 0,
				skipped: 0,
				errors: 0,
				warnings: [],
			});

		await user.click(screen.getByRole("button", { name: /import \(1\)/i }));
		await waitFor(() => {
			expect(
				screen.getByRole("button", { name: /import \(1\)/i }),
			).toBeDisabled();
		});

		expect(getFileInput()).toBeDisabled();
		await user.keyboard("{Escape}");
		await user.click(screen.getByRole("button", { name: "Close" }));
		expect(onOpenChange).not.toHaveBeenCalled();

		await act(async () => {
			rejectFirst(new Error("import failed"));
		});

		const alert = await screen.findByRole("alert");
		expect(alert).toHaveTextContent("import failed");
		expect(
			screen.getByRole("dialog", { name: /import tables/i }),
		).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: /import \(1\)/i }),
		).toBeEnabled();

		await user.click(screen.getByRole("button", { name: /import \(1\)/i }));

		await waitFor(() => {
			expect(mockImportEntities).toHaveBeenCalledTimes(2);
		});

		expect(mockToast.success).toHaveBeenCalledWith("Import completed");
		expect(
			await screen.findByRole("button", { name: /done/i }),
		).toBeVisible();
	});
});
