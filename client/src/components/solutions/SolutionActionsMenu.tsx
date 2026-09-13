import {
	Download,
	HardDriveUpload,
	Loader2,
	MoreVertical,
	Pencil,
	PowerOff,
	RefreshCw,
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
	busy?: boolean;
	exporting: boolean;
	/** Whether this install is currently inactive (status === "inactive"). */
	isInactive: boolean;
	onCapture: () => void;
	onExport: () => void;
	onUpdateAppSdks?: () => void;
	appSdkUpdateDisabled?: boolean;
	appSdkUpdating?: boolean;
	onEdit: () => void;
	/** Non-destructive uninstall → flips to inactive. Only shown when active. */
	onUninstall: () => void;
	/** Hard-delete: permanently destroys everything. Always available. */
	onHardDelete: () => void;
}

/**
 * Overflow menu for the secondary Solution actions. The primary action
 * ("Update…") stays a visible button on the detail header; everything else —
 * Capture, Export, Edit, Uninstall (non-destructive), and the permanent
 * Delete — collapses here, matching the platform's admin-detail convention.
 */
export function SolutionActionsMenu({
	exporting,
	busy = false,
	isInactive,
	onCapture,
	onExport,
	onUpdateAppSdks,
	appSdkUpdateDisabled = false,
	appSdkUpdating = false,
	onEdit,
	onUninstall,
	onHardDelete,
}: Props) {
	return (
		<DropdownMenu>
			<DropdownMenuTrigger asChild>
				<Button
					variant="outline"
					size="icon-lg"
					aria-label="More solution actions"
					data-testid="solution-actions"
				>
					<MoreVertical className="h-4 w-4" />
				</Button>
			</DropdownMenuTrigger>
			<DropdownMenuContent align="end" className="w-auto">
				<DropdownMenuItem
					disabled={busy}
					onClick={onCapture}
					className="min-h-11 whitespace-normal"
					data-testid="capture-solution"
				>
					<HardDriveUpload className="mr-2 h-4 w-4" />
					Capture Existing Entities
				</DropdownMenuItem>
				<DropdownMenuItem
					onClick={onExport}
					disabled={exporting || busy}
					className="min-h-11 whitespace-normal"
					data-testid="export-solution"
				>
					{exporting ? (
						<Loader2
							aria-hidden="true"
							className="mr-2 h-4 w-4 animate-spin motion-reduce:animate-none"
						/>
					) : (
						<Download className="mr-2 h-4 w-4" />
					)}
					Export Solution
				</DropdownMenuItem>
				{onUpdateAppSdks && (
					<DropdownMenuItem
						onClick={onUpdateAppSdks}
						disabled={busy || appSdkUpdateDisabled || appSdkUpdating}
						className="min-h-11 whitespace-normal"
						data-testid="update-solution-app-sdks"
					>
						{appSdkUpdating ? (
							<Loader2
								aria-hidden="true"
								className="mr-2 h-4 w-4 animate-spin motion-reduce:animate-none"
							/>
						) : (
							<RefreshCw className="mr-2 h-4 w-4" />
						)}
						{appSdkUpdating
							? "Updating app SDKs"
							: "Update app SDKs"}
					</DropdownMenuItem>
				)}
				<DropdownMenuItem
					disabled={busy}
					onClick={onEdit}
					className="min-h-11 whitespace-normal"
					data-testid="edit-solution"
				>
					<Pencil className="mr-2 h-4 w-4" />
					Edit Details
				</DropdownMenuItem>
				<DropdownMenuSeparator />
				{!isInactive && (
					<DropdownMenuItem
						disabled={busy}
						onClick={onUninstall}
						className="min-h-11 whitespace-normal"
						data-testid="uninstall-solution"
					>
						<PowerOff className="mr-2 h-4 w-4" />
						Uninstall
					</DropdownMenuItem>
				)}
				<DropdownMenuItem
					disabled={busy}
					onClick={onHardDelete}
					variant="destructive"
					className="min-h-11 whitespace-normal"
					data-testid="hard-delete-solution"
				>
					<Trash2 className="mr-2 h-4 w-4" />
					Delete permanently
				</DropdownMenuItem>
			</DropdownMenuContent>
		</DropdownMenu>
	);
}
