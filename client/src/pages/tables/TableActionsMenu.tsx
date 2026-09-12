import { Pencil, Trash2 } from "lucide-react";
import { RecordActionsMenu } from "@/components/common/RecordActionsMenu";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import type { TablePublic } from "@/services/tables";

export function TableActionsMenu({
	table,
	onEdit,
	onDelete,
}: {
	table: TablePublic;
	onEdit: () => void;
	onDelete: () => void;
}) {
	return (
		<RecordActionsMenu label={`${table.name} actions`}>
			<DropdownMenuItem
				className="min-h-11"
				disabled={table.is_solution_managed}
				onSelect={onEdit}
			>
				<Pencil aria-hidden="true" className="size-4" />
				Edit
			</DropdownMenuItem>
			<DropdownMenuItem
				variant="destructive"
				className="min-h-11"
				disabled={table.is_solution_managed}
				onSelect={onDelete}
			>
				<Trash2 aria-hidden="true" className="size-4" />
				Delete
			</DropdownMenuItem>
		</RecordActionsMenu>
	);
}
