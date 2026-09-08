import { describe, expect, it } from "vitest";
import { fireEvent, renderWithProviders, screen } from "@/test-utils";
import {
	ContextMenu,
	ContextMenuContent,
	ContextMenuTrigger,
} from "@/components/ui/context-menu";

import { EntryMenuItem, FileContextMenuContent } from "./fileContextMenu";

describe("EntryMenuItem", () => {
	it("renders the canonical labels and destructive tone", () => {
		renderWithProviders(
			<ContextMenu>
				<ContextMenuTrigger asChild>
					<button type="button">Open</button>
				</ContextMenuTrigger>
				<ContextMenuContent>
					<EntryMenuItem action="test" onSelect={() => {}} />
					<EntryMenuItem
						action="delete"
						onSelect={() => {}}
						destructive
					/>
				</ContextMenuContent>
			</ContextMenu>,
		);

		fireEvent.contextMenu(screen.getByRole("button", { name: "Open" }));

		const testItem = screen.getByRole("menuitem", { name: "Test Access" });
		expect(testItem).toBeInTheDocument();
		expect(testItem).toHaveClass("min-h-11");

		const deleteItem = screen.getByRole("menuitem", { name: "Delete" });
		expect(deleteItem).toHaveAttribute("data-variant", "destructive");
		expect(deleteItem).toHaveClass("min-h-11");
	});

	it("caps the menu width for narrow viewports", () => {
		renderWithProviders(
			<ContextMenu>
				<ContextMenuTrigger asChild>
					<button type="button">Open</button>
				</ContextMenuTrigger>
				<FileContextMenuContent>
					<EntryMenuItem action="preview" onSelect={() => {}} />
				</FileContextMenuContent>
			</ContextMenu>,
		);

		fireEvent.contextMenu(screen.getByRole("button", { name: "Open" }));

		expect(screen.getByRole("menu")).toHaveClass(
			"w-[min(16rem,calc(100vw-1rem))]",
		);
	});
});
