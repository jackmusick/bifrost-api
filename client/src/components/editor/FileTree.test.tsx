import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";

const mockUseFileTreeActions = vi.fn();
const mockRunPreflight = vi.fn();
const mockRegisterWorkflow = vi.fn();
const mockUseReloadWorkflowFile = vi.fn();

vi.mock("sonner", () => ({
	toast: {
		success: vi.fn(),
		error: vi.fn(),
		info: vi.fn(),
	},
}));

vi.mock("framer-motion", () => ({
	useReducedMotion: () => false,
}));

vi.mock("@/hooks/useFileTreeActions", () => ({
	useFileTreeActions: () => mockUseFileTreeActions(),
}));

vi.mock("@/hooks/useWorkflows", () => ({
	runPreflight: () => mockRunPreflight(),
	registerWorkflow: (...args: unknown[]) => mockRegisterWorkflow(...args),
	useReloadWorkflowFile: () => mockUseReloadWorkflowFile(),
}));

vi.mock("./FileTreeNode", () => ({
	FileTreeNode: ({ file }: { file: { name: string } }) => (
		<div data-testid="file-tree-node">{file.name}</div>
	),
}));

vi.mock("./WorkflowIdConflictDialog", () => ({
	WorkflowIdConflictDialog: () => null,
}));

import { FileTree } from "./FileTree";

function makeActions(overrides: Record<string, unknown> = {}) {
	return {
		files: [],
		isLoading: false,
		isFolderLoading: () => false,
		isFolderExpanded: () => false,
		openFile: null,
		creatingItem: null,
		creatingInFolder: null,
		newItemName: "",
		setNewItemName: vi.fn(),
		inputRef: { current: null },
		handleCreateFile: vi.fn(),
		handleCreateFolder: vi.fn(),
		handleCancelNewItem: vi.fn(),
		handleNewItemKeyDown: vi.fn(),
		handleInputMouseDown: vi.fn(),
		handleFileClick: vi.fn(),
		handleFolderToggle: vi.fn(),
		handleRefresh: vi.fn(),
		fileToDelete: null,
		setFileToDelete: vi.fn(),
		handleDelete: vi.fn(),
		handleConfirmDelete: vi.fn(),
		renamingFile: null,
		renameValue: "",
		setRenameValue: vi.fn(),
		renameInputRef: { current: null },
		handleRename: vi.fn(),
		handleSaveRename: vi.fn(),
		handleRenameKeyDown: vi.fn(),
		handleRenameInputMouseDown: vi.fn(),
		dragOverFolder: null,
		handleDragStart: vi.fn(),
		handleDragOver: vi.fn(),
		handleDragLeave: vi.fn(),
		handleDrop: vi.fn(),
		isProcessing: false,
		uploadConflict: null,
		uploadWorkflowConflicts: null,
		setUploadWorkflowConflicts: vi.fn(),
		...overrides,
	};
}

describe("FileTree", () => {
	beforeEach(() => {
		mockUseReloadWorkflowFile.mockReturnValue({ mutate: vi.fn() });
		mockRunPreflight.mockResolvedValue({
			valid: true,
			issues: [],
			warnings: [],
		});
		mockRegisterWorkflow.mockResolvedValue(undefined);
	});

	it("renders the canonical toolbar and empty state", () => {
		mockUseFileTreeActions.mockReturnValue(makeActions());
		renderWithProviders(<FileTree />);

		expect(screen.getByRole("button", { name: "New File" })).toHaveClass(
			"size-11",
		);
		expect(screen.getByRole("button", { name: "New Folder" })).toHaveClass(
			"size-11",
		);
		expect(screen.getByRole("button", { name: "Refresh" })).toHaveClass(
			"size-11",
		);
		expect(
			screen.getByRole("button", { name: "Preflight Check" }),
		).toHaveClass("size-11");
		expect(screen.getByText("No files found")).toBeInTheDocument();
		expect(
			screen.getByText(/Use the toolbar to create files and folders/i),
		).toBeInTheDocument();
	});

	it("shows the processing overlay when work is in flight", () => {
		mockUseFileTreeActions.mockReturnValue(
			makeActions({ isProcessing: true }),
		);
		renderWithProviders(<FileTree />);

		expect(screen.getByText("Processing...")).toBeInTheDocument();
	});
});
