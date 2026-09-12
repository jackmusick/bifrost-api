import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test-utils";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import {
	DataTable,
	DataTableBody,
	DataTableCell,
	DataTableRow,
} from "@/components/ui/data-table";
import { RecordActionsMenu } from "./RecordActionsMenu";

describe("RecordActionsMenu", () => {
	it("does not trigger the containing row action from its trigger or menu item", async () => {
		const onRowOpen = vi.fn();
		const onMenuAction = vi.fn();
		const { user } = renderWithProviders(
			<DataTable>
				<DataTableBody>
					<DataTableRow clickable onClick={onRowOpen}>
						<DataTableCell>Account record</DataTableCell>
						<DataTableCell>
							<RecordActionsMenu label="Account record actions">
								<DropdownMenuItem onSelect={onMenuAction}>
									Archive
								</DropdownMenuItem>
							</RecordActionsMenu>
						</DataTableCell>
					</DataTableRow>
				</DataTableBody>
			</DataTable>,
		);

		await user.click(
			screen.getByRole("button", { name: "Account record actions" }),
		);
		await user.click(screen.getByRole("menuitem", { name: "Archive" }));

		expect(onMenuAction).toHaveBeenCalledOnce();
		expect(onRowOpen).not.toHaveBeenCalled();
	});
});
