import {
	Download,
	Eye,
	FlaskConical,
	FolderPlus,
	ShieldCheck,
	ShieldPlus,
	Trash2,
	Upload,
} from "lucide-react";
import {
	ContextMenuItem,
	ContextMenuContent,
	ContextMenuSeparator,
} from "@/components/ui/context-menu";
import { cn } from "@/lib/utils";
import { DropdownMenuContent } from "@/components/ui/dropdown-menu";

/**
 * Canonical labels + icons for file/share/folder actions, shared by the tree
 * (ShareTree) and the file rows (FolderListing) so both menus read the same.
 * Test access uses a distinct flask icon (NOT the shield, which means policy).
 */
export const ENTRY_ACTION_META = {
	preview: { label: "Preview", icon: Eye },
	effective: { label: "Effective Access", icon: ShieldCheck },
	test: { label: "Test Access", icon: FlaskConical },
	policy: { label: "Manage Policy", icon: ShieldCheck },
	newPolicy: { label: "New Policy", icon: ShieldPlus },
	upload: { label: "Upload", icon: Upload },
	newFolder: { label: "New Folder", icon: FolderPlus },
	download: { label: "Download", icon: Download },
	delete: { label: "Delete", icon: Trash2 },
} as const;

export type EntryAction = keyof typeof ENTRY_ACTION_META;

export function EntryMenuItem({
	action,
	onSelect,
	destructive,
}: {
	action: EntryAction;
	onSelect: () => void;
	destructive?: boolean;
}) {
	const meta = ENTRY_ACTION_META[action];
	const Icon = meta.icon;
	return (
		<ContextMenuItem
			variant={destructive ? "destructive" : undefined}
			onSelect={onSelect}
			className="min-h-11"
		>
			<Icon className="h-4 w-4" /> {meta.label}
		</ContextMenuItem>
	);
}

export function FileContextMenuContent({
	children,
	className,
}: {
	children: React.ReactNode;
	className?: string;
}) {
	return (
		<ContextMenuContent
			className={cn("w-[min(16rem,calc(100vw-1rem))]", className)}
		>
			{children}
		</ContextMenuContent>
	);
}

export { ContextMenuSeparator };

export function FileDropdownMenuContent({ className, ...props }: React.ComponentProps<typeof DropdownMenuContent>) {
	return <DropdownMenuContent {...props} className={cn("w-[min(16rem,calc(100vw-1rem))]", className)} />;
}
