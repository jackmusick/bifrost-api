import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
	ChevronDown,
	ChevronRight,
	Folder,
	HardDrive,
	Lock,
	MoreHorizontal,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	ContextMenu,
	ContextMenuTrigger,
} from "@/components/ui/context-menu";
import {
	DropdownMenu,
	DropdownMenuItem,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { listShares, listStructure } from "@/services/fileStructure";
import {
	ENTRY_ACTION_META,
	EntryMenuItem,
	FileContextMenuContent,
	FileDropdownMenuContent,
} from "./fileContextMenu";
import { InlineLoader } from "./InlineLoader";

export type ShareTreeAction =
	"effective" | "test" | "newFolder" | "upload" | "newPolicy";

interface ShareTreeProps {
	scope: string | null;
	selectedLocation: string | null;
	selectedPrefix: string;
	readOnly?: boolean;
	onSelect: (location: string, prefix: string) => void;
	onContextAction: (
		action: ShareTreeAction,
		location: string,
		prefix: string,
	) => void;
}

interface NodeProps extends ShareTreeProps {
	location: string;
	prefix: string;
	name: string;
	depth: number;
}

function LoadError({
	label,
	retry,
	pending,
}: {
	label: string;
	retry: () => void;
	pending: boolean;
}) {
	return (
		<div role="alert" className="space-y-1 px-2 py-2 text-sm">
			<p className="text-destructive">{label} could not be loaded.</p>
			<Button
				variant="outline"
				className="min-h-11"
				disabled={pending}
				onClick={retry}
			>
				Retry {label.toLowerCase()}
			</Button>
		</div>
	);
}

function BrowseNode(props: NodeProps) {
	const {
		location,
		prefix,
		name,
		depth,
		scope,
		readOnly,
		selectedLocation,
		selectedPrefix,
		onSelect,
		onContextAction,
	} = props;
	const active = selectedLocation === location;
	const [expanded, setExpanded] = useState(
		active && (prefix === "" || selectedPrefix.startsWith(`${prefix}/`)),
	);
	const selected = active && selectedPrefix === prefix;
	const children = useQuery({
		queryKey: ["file-structure", scope, location, prefix],
		queryFn: () => listStructure(location, prefix, scope),
		enabled: expanded,
		retry: false,
	});
	const folders =
		children.data?.filter((entry) => entry.kind === "folder") ?? [];
	const actions: ShareTreeAction[] = readOnly
		? ["effective", "test"]
		: ["effective", "test", "upload", "newPolicy"];
	const Icon = prefix === "" ? HardDrive : Folder;

	return (
		<li className="min-w-0">
			<ContextMenu>
				<ContextMenuTrigger asChild>
					<div
						className={`flex min-w-0 items-start rounded-[var(--bf-radius-control)] ${selected ? "bg-muted" : ""}`}
					>
						<Button
							variant="ghost"
							size="icon-lg"
							className="shrink-0"
							aria-label={`${expanded ? "Collapse" : "Expand"} ${name}`}
							aria-expanded={expanded}
							onClick={() => setExpanded((value) => !value)}
						>
							{expanded ? (
								<ChevronDown aria-hidden="true" />
							) : (
								<ChevronRight aria-hidden="true" />
							)}
						</Button>
						<button
							type="button"
							aria-current={selected ? "location" : undefined}
							onClick={() => onSelect(location, prefix)}
							className="flex min-h-11 min-w-0 flex-1 items-start gap-2 rounded-[var(--bf-radius-control)] px-1 py-3 text-left text-sm transition-colors duration-(--bf-motion-feedback) hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring motion-reduce:transition-none"
						>
							<Icon
								aria-hidden="true"
								className="mt-0.5 size-4 shrink-0 text-muted-foreground"
							/>
							<span
								className={`min-w-0 [overflow-wrap:anywhere] ${selected ? "font-medium" : ""}`}
							>
								{name}
								{prefix === "" && readOnly && (
									<span className="mt-1 flex items-center gap-1 text-xs font-normal text-muted-foreground">
										<Lock
											aria-hidden="true"
											className="size-3"
										/>
										Read-only
									</span>
								)}
							</span>
						</button>
						<DropdownMenu>
							<DropdownMenuTrigger asChild>
								<Button
									variant="ghost"
									size="icon-lg"
									className="shrink-0"
									aria-label={`Actions for ${name}`}
								>
									<MoreHorizontal aria-hidden="true" />
								</Button>
							</DropdownMenuTrigger>
							<FileDropdownMenuContent align="end">
								{actions.map((action) => {
									const meta = ENTRY_ACTION_META[action];
									const ActionIcon = meta.icon;
									return (
										<DropdownMenuItem
											key={action}
											className="min-h-11"
											onSelect={() =>
												onContextAction(
													action,
													location,
													prefix,
												)
											}
										>
											<ActionIcon aria-hidden="true" />
											{meta.label}
										</DropdownMenuItem>
									);
								})}
							</FileDropdownMenuContent>
						</DropdownMenu>
					</div>
				</ContextMenuTrigger>
				<FileContextMenuContent>
					{actions.map((action) => (
						<EntryMenuItem
							key={action}
							action={action}
							onSelect={() =>
								onContextAction(action, location, prefix)
							}
						/>
					))}
				</FileContextMenuContent>
			</ContextMenu>
			{expanded && (
				<div
					className={
						depth < 4
							? "ml-3 border-l border-border pl-1"
							: "border-l border-border pl-1"
					}
				>
					{children.isPending && (
						<InlineLoader
							className="px-2 py-3"
							label={`Loading folders in ${name}…`}
						/>
					)}
					{children.isError && (
						<LoadError
							label="Folders"
							retry={() => void children.refetch()}
							pending={children.isFetching}
						/>
					)}
					{children.isSuccess && folders.length === 0 && (
						<p className="px-2 py-3 text-xs text-muted-foreground">
							No subfolders
						</p>
					)}
					{folders.length > 0 && (
						<ul aria-label={`Folders in ${name}`}>
							{folders.map((folder) => (
								<BrowseNode
									{...props}
									key={folder.path}
									prefix={folder.path}
									name={folder.name}
									depth={depth + 1}
								/>
							))}
						</ul>
					)}
				</div>
			)}
		</li>
	);
}

function ShareNavigation(props: ShareTreeProps) {
	const shares = useQuery({
		queryKey: ["file-shares", props.scope],
		queryFn: () => listShares(props.scope),
		retry: false,
	});
	return (
		<nav
			aria-label="File shares"
			className="min-h-0 min-w-0 flex-1 overflow-auto p-2"
		>
			{shares.isPending && (
				<InlineLoader className="px-2 py-3" label="Loading shares…" />
			)}
			{shares.isError && (
				<LoadError
					label="Shares"
					retry={() => void shares.refetch()}
					pending={shares.isFetching}
				/>
			)}
			{shares.isSuccess && shares.data.length === 0 && (
				<p className="px-2 py-3 text-sm text-muted-foreground">
					{props.readOnly
						? "No shares in this scope."
						: "No shares in this scope. Create one with “New share”."}
				</p>
			)}
			{!!shares.data?.length && (
				<ul>
					{shares.data.map((share) => (
						<BrowseNode
							{...props}
							key={share.location}
							location={share.location}
							prefix=""
							name={share.location}
							depth={0}
							readOnly={props.readOnly || share.readOnly}
						/>
					))}
				</ul>
			)}
		</nav>
	);
}

export function ShareTree(props: ShareTreeProps) {
	return <ShareNavigation key={props.scope ?? "global"} {...props} />;
}
