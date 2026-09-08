import { Circle, FileCode, Workflow } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "@/components/ui/popover";

interface EditorFileStatusProps {
	path: string;
	isWorkflow: boolean;
	saveState: "clean" | "dirty" | "saving" | "saved" | "conflict";
	language: string;
	cursor: { line: number; column: number };
}

export function EditorFileStatus({
	path,
	isWorkflow,
	saveState,
	language,
	cursor,
}: EditorFileStatusProps) {
	const status = {
		clean: "",
		dirty: "Unsaved changes",
		saving: "Saving…",
		saved: "Saved",
		conflict: "Conflict with server version",
	}[saveState];
	return (
		<div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-3 gap-y-1">
			<Popover>
				<PopoverTrigger asChild>
					<Button
						variant="ghost"
						className="min-h-11 h-auto min-w-0 max-w-full justify-start px-1 py-2 font-mono text-sm sm:text-xs"
						aria-label={`File details for ${path}`}
					>
						<FileCode className="size-3.5 shrink-0" />
						<span className="min-w-0 truncate">
							{path.split("/").pop()}
						</span>
					</Button>
				</PopoverTrigger>
				<PopoverContent
					side="top"
					align="start"
					className="w-80 max-w-[calc(100vw-2rem)] max-h-(--radix-popover-content-available-height) overflow-y-auto"
				>
					<h4 className="text-sm font-semibold">File details</h4>
					<dl className="space-y-3 text-sm leading-5">
						<div>
							<dt className="text-muted-foreground">Path</dt>
							<dd className="mt-1 font-mono [overflow-wrap:anywhere]">
								{path}
							</dd>
						</div>
						<div>
							<dt className="text-muted-foreground">Language</dt>
							<dd className="mt-1 capitalize">
								{language || "Plain text"}
							</dd>
						</div>
						<div>
							<dt className="text-muted-foreground">Cursor</dt>
							<dd className="mt-1">
								Line {cursor.line}, column {cursor.column}
							</dd>
						</div>
					</dl>
				</PopoverContent>
			</Popover>
			{path.endsWith(".py") && (
				<Badge variant="secondary" className="h-auto text-xs">
					{isWorkflow && <Workflow className="size-3" />}
					{isWorkflow ? "Workflow" : "Python Script"}
				</Badge>
			)}
			{status && (
				<span
					role="status"
					className={`flex min-w-0 items-center gap-1 text-xs ${saveState === "saved" ? "text-[var(--bf-success)]" : saveState === "saving" ? "text-primary" : "text-[var(--bf-warning)]"}`}
				>
					<Circle className="size-2 shrink-0 fill-current" />
					<span className="[overflow-wrap:anywhere]">{status}</span>
				</span>
			)}
			<span className="ml-auto whitespace-nowrap text-xs tabular-nums">
				Ln {cursor.line}, Col {cursor.column}
			</span>
		</div>
	);
}
