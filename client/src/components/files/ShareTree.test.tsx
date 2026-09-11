import {
	renderWithProviders as render,
	screen,
	fireEvent,
	waitFor,
} from "@/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/services/fileStructure", () => ({
	listShares: vi.fn(),
	listStructure: vi.fn(),
}));
import { listShares, listStructure } from "@/services/fileStructure";
import { ShareTree } from "./ShareTree";

describe("ShareTree", () => {
	beforeEach(() => {
		vi.resetAllMocks();
		vi.mocked(listShares).mockResolvedValue([
			{ location: "gallery", readOnly: false, hasPolicy: true },
			{ location: "uploads", readOnly: true, hasPolicy: false },
		]);
		vi.mocked(listStructure).mockResolvedValue([
			{ name: "team", kind: "folder", path: "team" },
		]);
	});

	it("lists shares and marks uploads read-only", async () => {
		render(
			<ShareTree
				scope={null}
				selectedLocation={null}
				selectedPrefix=""
				onSelect={vi.fn()}
				onContextAction={vi.fn()}
			/>,
		);
		expect(await screen.findByText("gallery")).toBeInTheDocument();
		expect(screen.getByText("uploads")).toBeInTheDocument();
		expect(screen.getByText(/read-only/i)).toBeInTheDocument();
	});

	it("selects a share on click and lazy-loads its folders", async () => {
		const onSelect = vi.fn();
		render(
			<ShareTree
				scope={null}
				selectedLocation="gallery"
				selectedPrefix=""
				onSelect={onSelect}
				onContextAction={vi.fn()}
			/>,
		);
		fireEvent.click(await screen.findByText("gallery"));
		expect(onSelect).toHaveBeenCalledWith("gallery", "");
		await waitFor(() =>
			expect(listStructure).toHaveBeenCalledWith("gallery", "", null),
		);
		const folder = await screen.findByText("team");
		expect(folder).toBeInTheDocument();
		const selectedRow = screen.getByRole("button", { name: "gallery" })
			.parentElement;
		expect(selectedRow).toHaveClass("tree-row-selected", "z-20");
		expect(selectedRow?.closest("li")).not.toHaveClass("tree-row-selected");
		expect(folder.closest("li")).toHaveClass("before:absolute");
	});
	it("expands separately from navigation and retries failed folder loads", async () => {
		const onSelect = vi.fn();
		vi.mocked(listStructure).mockRejectedValueOnce(
			new Error("Unavailable"),
		);
		render(
			<ShareTree
				scope="org-1"
				selectedLocation={null}
				selectedPrefix=""
				onSelect={onSelect}
				onContextAction={vi.fn()}
			/>,
		);
		fireEvent.click(
			await screen.findByRole("button", { name: "Expand gallery" }),
		);
		expect(onSelect).not.toHaveBeenCalled();
		expect(await screen.findByRole("alert")).toHaveTextContent(
			"Folders could not be loaded",
		);
		expect(screen.queryByText("No subfolders")).not.toBeInTheDocument();
		fireEvent.click(screen.getByRole("button", { name: "Retry folders" }));
		fireEvent.click(await screen.findByRole("button", { name: "team" }));
		expect(onSelect).toHaveBeenCalledWith("gallery", "team");
		expect(listStructure).toHaveBeenLastCalledWith("gallery", "", "org-1");
	});

	it("retries a failed share load without suggesting that the scope is empty", async () => {
		vi.mocked(listShares).mockRejectedValueOnce(new Error("Unavailable"));
		render(
			<ShareTree
				scope={null}
				selectedLocation={null}
				selectedPrefix=""
				onSelect={vi.fn()}
				onContextAction={vi.fn()}
			/>,
		);
		expect(await screen.findByRole("alert")).toHaveTextContent(
			"Shares could not be loaded",
		);
		expect(screen.queryByText(/No shares/)).not.toBeInTheDocument();
		fireEvent.click(screen.getByRole("button", { name: "Retry shares" }));
		expect(
			await screen.findByRole("button", { name: "gallery" }),
		).toBeInTheDocument();
	});

	it("provides explicit actions while keeping read-only shares protected", async () => {
		const onContextAction = vi.fn();
		render(
			<ShareTree
				scope={null}
				selectedLocation={null}
				selectedPrefix=""
				onSelect={vi.fn()}
				onContextAction={onContextAction}
			/>,
		);
		fireEvent.pointerDown(
			await screen.findByRole("button", { name: "Actions for uploads" }),
			{ button: 0, ctrlKey: false },
		);
		expect(
			await screen.findByRole("menuitem", { name: "Test Access" }),
		).toBeInTheDocument();
		expect(
			screen.queryByRole("menuitem", { name: "Upload" }),
		).not.toBeInTheDocument();
		expect(
			screen.queryByRole("menuitem", { name: "New Policy" }),
		).not.toBeInTheDocument();
		fireEvent.click(screen.getByRole("menuitem", { name: "Test Access" }));
		expect(onContextAction).toHaveBeenCalledWith("test", "uploads", "");
	});
});
