import { ChevronRight, MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useMediaQuery } from "@/hooks/useMediaQuery";

interface BreadcrumbsProps {
	scopeLabel: string;
	/** Solution views navigate within a share and omit the organization root. */
	includeScopeRoot?: boolean;
	location: string | null;
	segments: string[];
	/** -1: scope root; 0: share root; n: after the nth path segment. */
	onNavigate: (depth: number) => void;
}

export function Breadcrumbs({
	scopeLabel,
	includeScopeRoot = true,
	location,
	segments,
	onNavigate,
}: BreadcrumbsProps) {
	const mobile = useMediaQuery("(max-width: 1023px)");
	const crumbs = [
		...(includeScopeRoot ? [{ label: scopeLabel, depth: -1 }] : []),
		...(location === null
			? []
			: [
					{ label: location, depth: 0 },
					...segments.map((label, index) => ({
						label,
						depth: index + 1,
					})),
				]),
	];
	if (crumbs.length === 0) return null;
	const current = crumbs[crumbs.length - 1];
	const collapse = mobile ? crumbs.length > 1 : crumbs.length > 5;
	const visible = collapse ? [current] : crumbs;
	return (
		<nav aria-label="Breadcrumb" className="min-w-0 flex-1 overflow-hidden">
			<ol className="no-scrollbar flex min-w-0 items-center gap-1 overflow-x-auto overscroll-x-contain whitespace-nowrap">
				{collapse && (
					<li className="flex shrink-0 items-center gap-1">
						<DropdownMenu>
							<DropdownMenuTrigger asChild>
								<Button
									variant="ghost"
									size="icon-lg"
									aria-label="Parent locations"
								>
									<MoreHorizontal aria-hidden="true" />
								</Button>
							</DropdownMenuTrigger>
							<DropdownMenuContent
								align="start"
								className="max-h-[var(--radix-dropdown-menu-content-available-height)] max-w-[calc(100vw-2rem)] overflow-y-auto"
							>
								{crumbs.slice(0, -1).map((crumb) => (
									<DropdownMenuItem
										key={crumb.depth}
										className="min-h-11 whitespace-normal [overflow-wrap:anywhere]"
										onSelect={() => onNavigate(crumb.depth)}
									>
										{crumb.label}
									</DropdownMenuItem>
								))}
							</DropdownMenuContent>
						</DropdownMenu>
						<ChevronRight
							aria-hidden="true"
							className="size-3 text-muted-foreground"
						/>
					</li>
				)}
				{visible.map((crumb, index) => (
					<li
						key={crumb.depth}
						className={`flex min-w-0 items-center gap-1 ${collapse ? "flex-1" : "shrink-0"}`}
					>
						{index > 0 && (
							<ChevronRight
								aria-hidden="true"
								className="size-3 shrink-0 text-muted-foreground"
							/>
						)}
						<button
							type="button"
							aria-current={
								crumb.depth === current.depth
									? "location"
									: undefined
							}
							onClick={() => onNavigate(crumb.depth)}
							className={`min-h-9 max-w-[16rem] truncate rounded-[var(--bf-radius-control)] px-2 py-1.5 text-left text-sm transition-colors duration-(--bf-motion-feedback) hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring motion-reduce:transition-none sm:max-w-[22rem] ${collapse ? "min-w-0 flex-1" : ""} ${crumb.depth === current.depth ? "font-medium text-foreground" : "text-muted-foreground"}`}
						>
							{crumb.label}
						</button>
					</li>
				))}
			</ol>
		</nav>
	);
}
