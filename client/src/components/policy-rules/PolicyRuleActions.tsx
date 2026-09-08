import { Pencil, Trash2 } from "lucide-react";
import { RecordActionsMenu } from "@/components/common/RecordActionsMenu";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import type { PolicyRule } from "@/services/policyRules";
export function PolicyRuleActions({
	rule,
	onEdit,
	onDelete,
}: {
	rule: PolicyRule;
	onEdit: () => void;
	onDelete: () => void;
}) {
	if (rule.is_builtin) return null;
	return (
		<RecordActionsMenu label={`${rule.name} actions`}>
			<DropdownMenuItem
				className="min-h-11"
				onSelect={onEdit}
				data-testid="policy-rule-edit-btn"
			>
				<Pencil aria-hidden="true" className="size-4" />
				Edit
			</DropdownMenuItem>
			<DropdownMenuItem
				className="min-h-11"
				variant="destructive"
				onSelect={onDelete}
				data-testid="policy-rule-delete-btn"
			>
				<Trash2 aria-hidden="true" className="size-4" />
				Delete
			</DropdownMenuItem>
		</RecordActionsMenu>
	);
}
