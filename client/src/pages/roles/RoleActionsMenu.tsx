import { Pencil, Trash2 } from "lucide-react";
import { RecordActionsMenu } from "@/components/common/RecordActionsMenu";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";

export function RoleActionsMenu({
	name,
	onEdit,
	onDelete,
}: {
	name: string;
	onEdit: () => void;
	onDelete: () => void;
}) {
	return (
		<RecordActionsMenu label={`${name} actions`}>
			<DropdownMenuItem className="min-h-11" onSelect={onEdit}>
				<Pencil aria-hidden="true" className="size-4" />
				Edit
			</DropdownMenuItem>
			<DropdownMenuItem
				variant="destructive"
				className="min-h-11"
				onSelect={onDelete}
			>
				<Trash2 aria-hidden="true" className="size-4" />
				Delete
			</DropdownMenuItem>
		</RecordActionsMenu>
	);
}
