import {
	Ban,
	Link as LinkIcon,
	Mail,
	MoreVertical,
	RefreshCw,
	Power,
	Trash2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface Props {
	label?: string;
	status: string;
	isActive: boolean;
	isSelf: boolean;
	onResend: () => void;
	onRegenerate: () => void;
	onCopyLink: () => void;
	onRevoke: () => void;
	onToggleActive: () => void;
	onDelete: () => void;
}

export function UserActionsMenu({
	label = "User actions",
	status,
	isActive,
	isSelf,
	onResend,
	onRegenerate,
	onCopyLink,
	onRevoke,
	onToggleActive,
	onDelete,
}: Props) {
	const showInviteActions = status !== "active";
	const hasActiveInvite = status === "pending" || status === "expired";

	return (
		<DropdownMenu>
			<DropdownMenuTrigger asChild>
				<Button
					variant="ghost"
					size="icon"
					aria-label={label}
					className="h-11 w-11 shrink-0 lg:h-9 lg:w-9"
				>
					<MoreVertical className="h-4 w-4" />
				</Button>
			</DropdownMenuTrigger>
			<DropdownMenuContent
				align="end"
				className="w-max min-w-40 whitespace-nowrap"
				onClick={(e) => e.stopPropagation()}
			>
				{showInviteActions && (
					<>
						<DropdownMenuItem
							className="min-h-11 lg:min-h-9"
							onClick={onResend}
						>
							<Mail className="h-4 w-4" />
							{hasActiveInvite ? "Resend invite" : "Send invite"}
						</DropdownMenuItem>
						<DropdownMenuItem
							className="min-h-11 lg:min-h-9"
							onClick={onRegenerate}
						>
							<RefreshCw className="h-4 w-4" />
							Generate registration link
						</DropdownMenuItem>
						<DropdownMenuItem
							className="min-h-11 lg:min-h-9"
							onClick={onCopyLink}
						>
							<LinkIcon className="h-4 w-4" />
							Copy registration link
						</DropdownMenuItem>
						{hasActiveInvite && (
							<DropdownMenuItem
								variant="destructive"
								onClick={onRevoke}
								className="min-h-11 lg:min-h-9"
							>
								<Ban className="h-4 w-4" />
								Revoke invite
							</DropdownMenuItem>
						)}
						<DropdownMenuSeparator />
					</>
				)}
				<DropdownMenuItem
					className="min-h-11 lg:min-h-9"
					onClick={onToggleActive}
					disabled={isSelf}
				>
					<Power className="h-4 w-4" />
					{isActive ? "Disable" : "Enable"}
				</DropdownMenuItem>
				<DropdownMenuItem
					variant="destructive"
					onClick={onDelete}
					disabled={isSelf}
					className="min-h-11 lg:min-h-9"
				>
					<Trash2 className="h-4 w-4" />
					Delete
				</DropdownMenuItem>
			</DropdownMenuContent>
		</DropdownMenu>
	);
}
