import { ChevronRight, Database } from "lucide-react";
import { Link } from "react-router-dom";
import { MarkdownContent } from "@/components/common/MarkdownContent";
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
		<header className="shrink-0 border-b border-border/70 px-4">
			<nav
				aria-label="Table navigation"
				className="flex min-h-12 min-w-0 items-center gap-2 text-sm"
			>
				<Link
					to={backTo}
					aria-label={backLabel}
					className="flex min-h-11 shrink-0 items-center gap-2 text-muted-foreground hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
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
			</nav>
			{description && (
				<MarkdownContent
					content={description}
					variant="preview"
					className="line-clamp-2 pb-3 text-xs text-muted-foreground"
				/>
			)}
		</header>
	);
}
