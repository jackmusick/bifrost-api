import { useRef } from "react";
import {
	FileSpreadsheet,
	FileText,
	Image,
	MoreVertical,
	Pencil,
	Presentation,
	Trash2,
	Video,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import {
	formatBytes,
	isImageAttachment,
	isVideoAttachment,
	type ChatArtifactPublic,
} from "@/services/chatAttachments";

function ArtifactIcon({ artifact }: { artifact: ChatArtifactPublic }) {
	if (isImageAttachment(artifact.content_type)) return <Image className="h-5 w-5" />;
	if (isVideoAttachment(artifact.content_type)) return <Video className="h-5 w-5" />;
	if (artifact.content_type.includes("spreadsheet")) {
		return <FileSpreadsheet className="h-5 w-5" />;
	}
	if (artifact.content_type.includes("presentation")) {
		return <Presentation className="h-5 w-5" />;
	}
	return <FileText className="h-5 w-5" />;
}

function formatArtifactDate(value: string): string {
	return new Intl.DateTimeFormat(undefined, {
		month: "short",
		day: "numeric",
		year: "numeric",
	}).format(new Date(value));
}

export function ArtifactRecord({
	artifact,
	onPreview,
	onRename,
	onDelete,
}: {
	artifact: ChatArtifactPublic;
	onPreview: (artifact: ChatArtifactPublic) => void;
	onRename: (artifact: ChatArtifactPublic, trigger: HTMLButtonElement) => void;
	onDelete: (artifact: ChatArtifactPublic, trigger: HTMLButtonElement) => void;
}) {
	const manageButtonRef = useRef<HTMLButtonElement>(null);

	return (
		<li className="flex min-h-16 items-start gap-2 p-4 hover:bg-muted/40">
			<button
				type="button"
				aria-label={`Preview ${artifact.filename}`}
				onClick={() => onPreview(artifact)}
				className="flex min-h-11 min-w-0 flex-1 items-start gap-3 rounded-[var(--bf-radius-control)] text-left outline-none focus-visible:ring-2 focus-visible:ring-ring"
			>
				<span
					className={cn(
						"flex h-10 w-10 shrink-0 items-center justify-center rounded-[var(--bf-radius-control)]",
						artifact.kind === "artifact"
							? "bg-primary/10 text-primary"
							: "bg-muted text-muted-foreground",
					)}
				>
					<ArtifactIcon artifact={artifact} />
				</span>
				<span className="min-w-0 flex-1">
					<span className="block text-sm font-medium [overflow-wrap:anywhere]">
						{artifact.filename}
					</span>
					<span className="mt-1 block text-xs text-muted-foreground [overflow-wrap:anywhere]">
						{artifact.kind === "artifact" ? "Generated" : "Uploaded"} ·{" "}
						{formatBytes(artifact.size_bytes)}
						{artifact.conversation_title
							? ` · ${artifact.conversation_title}`
							: ""}{" "}
						· {formatArtifactDate(artifact.created_at)}
					</span>
				</span>
			</button>

			<DropdownMenu>
				<DropdownMenuTrigger asChild>
					<Button
						ref={manageButtonRef}
						variant="ghost"
						size="icon-sm"
						className="size-11 shrink-0"
						aria-label={`Manage ${artifact.filename}`}
					>
						<MoreVertical className="h-4 w-4" />
					</Button>
				</DropdownMenuTrigger>
				<DropdownMenuContent align="end">
					<DropdownMenuItem
						onSelect={() => {
							if (manageButtonRef.current) {
								onRename(artifact, manageButtonRef.current);
							}
						}}
					>
						<Pencil /> Rename
					</DropdownMenuItem>
					<DropdownMenuItem
						variant="destructive"
						onSelect={() => {
							if (manageButtonRef.current) {
								onDelete(artifact, manageButtonRef.current);
							}
						}}
					>
						<Trash2 /> Delete
					</DropdownMenuItem>
				</DropdownMenuContent>
			</DropdownMenu>
		</li>
	);
}
