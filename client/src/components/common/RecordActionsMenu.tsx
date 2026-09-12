import type { ReactNode } from "react";
import { MoreVertical } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

/** Shared row/card affordance; callers own actions and permission rules. */
export function RecordActionsMenu({
	label,
	children,
	contentClassName = "",
}: {
	label: string;
	children: ReactNode;
	contentClassName?: string;
}) {
	return (
		<DropdownMenu>
			<DropdownMenuTrigger asChild>
				<Button
					type="button"
					variant="ghost"
					size="icon-lg"
					aria-label={label}
					onClick={(event) => event.stopPropagation()}
				>
					<MoreVertical aria-hidden="true" className="size-4" />
				</Button>
			</DropdownMenuTrigger>
			<DropdownMenuContent
				align="end"
				className={`min-w-40 ${contentClassName}`}
				onClick={(event) => event.stopPropagation()}
			>
				{children}
			</DropdownMenuContent>
		</DropdownMenu>
	);
}
