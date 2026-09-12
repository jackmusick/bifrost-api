import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
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
		<header className="shrink-0 space-y-2">
			<Button
				type="button"
				variant="ghost"
				asChild
				className="-ml-2 min-h-11 px-2"
			>
				<Link to={backTo}>
					<ArrowLeft aria-hidden="true" className="size-4" />
					{backLabel}
				</Link>
			</Button>
			<h1 className="font-display text-2xl font-semibold tracking-tight [overflow-wrap:anywhere]">
				{name}
			</h1>
			{description && (
				<MarkdownContent
					content={description}
					variant="preview"
					className="max-w-3xl text-sm text-muted-foreground"
				/>
			)}
		</header>
	);
}
