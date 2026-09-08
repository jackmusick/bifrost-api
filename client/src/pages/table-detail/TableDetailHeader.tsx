import { ArrowLeft, Plus, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ListPageHeader } from "@/components/layout/ListPageHeader";

interface Props {
	name: string;
	description: string | null | undefined;
	backTo: string;
	backLabel: string;
	refreshing: boolean;
	onRefresh: () => void;
	onAdd: () => void;
}

export function TableDetailHeader({
	name,
	description,
	backTo,
	backLabel,
	refreshing,
	onRefresh,
	onAdd,
}: Props) {
	return (
		<header className="space-y-3">
			<Button
				type="button"
				variant="ghost"
				asChild
				className="min-h-11 px-2"
			>
				<Link to={backTo}>
					<ArrowLeft aria-hidden="true" className="size-4" />
					{backLabel}
				</Link>
			</Button>
			<ListPageHeader
				title={name}
				titleClassName="[overflow-wrap:anywhere]"
				description={description}
				descriptionClassName="[overflow-wrap:anywhere]"
				actionsClassName="grid grid-cols-[auto_1fr] sm:flex sm:shrink-0"
				actions={
					<>
						<Button
							type="button"
							variant="outline"
							size="icon-lg"
							aria-label="Refresh documents"
							disabled={refreshing}
							onClick={onRefresh}
						>
							<RefreshCw
								aria-hidden="true"
								className={
									refreshing
										? "size-4 animate-spin motion-reduce:animate-none"
										: "size-4"
								}
							/>
						</Button>
						<Button
							type="button"
							className="min-h-11"
							onClick={onAdd}
						>
							<Plus aria-hidden="true" className="size-4" />
							Add document
						</Button>
					</>
				}
			/>
		</header>
	);
}
