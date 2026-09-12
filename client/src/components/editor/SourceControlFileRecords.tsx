import { FileCode, FileText, Bot, Workflow, AppWindow } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { ChangedFile, MergeConflict } from "@/hooks/useGitHub";

function FileIdentity({ file }: { file: ChangedFile | MergeConflict }) {
	const icons = {
		form: FileText,
		agent: Bot,
		workflow: Workflow,
		app: AppWindow,
		app_file: FileCode,
	};
	const Icon = icons[file.entity_type as keyof typeof icons] ?? FileCode;
	return (
		<>
			<span className="flex min-w-0 items-start gap-2">
				<Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
				<span className="min-w-0 text-sm font-medium [overflow-wrap:anywhere]">
					{file.display_name || file.path}
				</span>
			</span>
			{file.display_name && file.display_name !== file.path && (
				<span className="block font-mono text-xs text-muted-foreground [overflow-wrap:anywhere]">
					{file.path}
				</span>
			)}
			{file.entity_type && (
				<span className="block text-xs text-muted-foreground">
					{file.entity_type.replaceAll("_", " ")}
				</span>
			)}
		</>
	);
}

export function ChangedFileRecord({
	file,
	disabled,
	discardDisabled,
	onShowDiff,
	onDiscard,
}: {
	file: ChangedFile;
	disabled?: boolean;
	discardDisabled?: boolean;
	onShowDiff: () => void;
	onDiscard?: (() => void) | undefined;
}) {
	return (
		<article
			aria-label={`Changed file ${file.path}`}
			className="min-w-0 space-y-2 border-b py-3"
		>
			<button
				type="button"
				disabled={disabled}
				aria-label={`View changes for ${file.path}`}
				onClick={onShowDiff}
				className="min-h-11 w-full space-y-2 rounded-[var(--bf-radius-control)] p-2 text-left hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring disabled:opacity-50"
			>
				<FileIdentity file={file} />
			</button>
			<div className="flex flex-wrap items-center justify-between gap-2 px-2">
				<Badge variant="secondary" className="h-auto capitalize">
					{file.change_type}
				</Badge>
				{onDiscard && (
					<Button
						type="button"
						variant="ghost"
						disabled={disabled || discardDisabled}
						className="min-h-11 h-auto whitespace-normal text-destructive hover:text-destructive"
						aria-label={`Discard changes to ${file.path}`}
						onClick={onDiscard}
					>
						Discard changes
					</Button>
				)}
			</div>
		</article>
	);
}

export function ConflictFileRecord({
	conflict,
	resolution,
	disabled,
	onShowDiff,
	onResolve,
}: {
	conflict: MergeConflict;
	resolution?: "ours" | "theirs" | undefined;
	disabled?: boolean;
	onShowDiff: () => void;
	onResolve: (resolution: "ours" | "theirs") => void;
}) {
	return (
		<article
			aria-label={`Conflicted file ${conflict.path}`}
			className="min-w-0 space-y-2 border-b py-3"
		>
			<button
				type="button"
				disabled={disabled}
				aria-label={`Review conflict for ${conflict.path}`}
				onClick={onShowDiff}
				className="min-h-11 w-full space-y-2 rounded-[var(--bf-radius-control)] p-2 text-left hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring disabled:opacity-50"
			>
				<FileIdentity file={conflict} />
			</button>
			<p className="px-2 text-xs text-muted-foreground">
				{resolution
					? `${resolution === "ours" ? "Local" : "Remote"} version selected`
					: "Choose a version to resolve this conflict"}
			</p>
			<div
				role="group"
				aria-label={`Version to keep for ${conflict.path}`}
				className="flex flex-wrap gap-2 px-2"
			>
				<Button
					type="button"
					disabled={disabled}
					variant={resolution === "ours" ? "secondary" : "outline"}
					aria-pressed={resolution === "ours"}
					className="min-h-11 h-auto whitespace-normal px-3"
					onClick={() => onResolve("ours")}
				>
					Keep local
				</Button>
				<Button
					type="button"
					disabled={disabled}
					variant={resolution === "theirs" ? "secondary" : "outline"}
					aria-pressed={resolution === "theirs"}
					className="min-h-11 h-auto whitespace-normal px-3"
					onClick={() => onResolve("theirs")}
				>
					Keep remote
				</Button>
			</div>
		</article>
	);
}
