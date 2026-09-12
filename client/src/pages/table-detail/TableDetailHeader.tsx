import { ChevronRight, Database, Info } from "lucide-react";
import { Link } from "react-router-dom";
import { MarkdownContent } from "@/components/common/MarkdownContent";
import { WorkspaceHeader } from "@/components/layout/WorkspaceHeader";
import { Button } from "@/components/ui/button";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "@/components/ui/popover";

interface Props {
	name: string;
	description: string | null | undefined;
	backTo: string;
	backLabel: string;
}

export function TableDetailHeader({
	name,
	description,
	backTo,
	backLabel,
}: Props) {
	return (
		<WorkspaceHeader>
			<nav
				aria-label="Table navigation"
				className="flex min-w-0 flex-1 items-center gap-2 px-4 text-sm"
			>
				<Link
					to={backTo}
					aria-label={backLabel}
					className="flex h-full shrink-0 items-center gap-2 text-muted-foreground hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
				>
					<Database aria-hidden="true" className="size-4" />
					{backLabel === "Back to Solution" ? "Solution" : "Tables"}
				</Link>
				<ChevronRight
					aria-hidden="true"
					className="size-4 shrink-0 text-muted-foreground"
				/>
				<h2 className="min-w-0 truncate font-semibold" title={name}>
					{name}
				</h2>
				{description && (
					<Popover>
						<PopoverTrigger asChild>
							<Button
								variant="ghost"
								size="icon"
								className="ml-auto shrink-0"
								aria-label="About This Table"
							>
								<Info className="size-4" />
							</Button>
						</PopoverTrigger>
						<PopoverContent
							align="end"
							className="max-h-80 w-80 max-w-[calc(100vw-2rem)] overflow-y-auto"
						>
							<MarkdownContent content={description} />
						</PopoverContent>
					</Popover>
				)}
			</nav>
		</WorkspaceHeader>
	);
}
