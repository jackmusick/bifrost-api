import { useState, useMemo } from "react";
import { Building2, ChevronDown, Globe, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuLabel,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import type { OrgScope } from "@/contexts/OrgScopeContext";
import type { components } from "@/lib/v1";
type Organization = components["schemas"]["OrganizationPublic"];

interface OrgScopeSwitcherProps {
	scope: OrgScope;
	setScope: (scope: OrgScope) => void;
	organizations: Organization[] | undefined;
	isLoading: boolean;
	isGlobalScope: boolean;
}

export function OrgScopeSwitcher({
	scope,
	setScope,
	organizations,
	isLoading,
	isGlobalScope,
}: OrgScopeSwitcherProps) {
	const [searchQuery, setSearchQuery] = useState("");
	const [isOpen, setIsOpen] = useState(false);

	// Filter organizations based on search query
	const filteredOrgs = useMemo(() => {
		if (!organizations) return [];
		if (!searchQuery.trim()) return organizations;

		const query = searchQuery.toLowerCase();
		return organizations.filter(
			(org) =>
				org.name.toLowerCase().includes(query) ||
				org.id.toLowerCase().includes(query),
		);
	}, [organizations, searchQuery]);

	// Clear search when dropdown closes
	const handleOpenChange = (open: boolean) => {
		setIsOpen(open);
		if (!open) {
			setSearchQuery("");
		}
	};

	const handleSelectOrg = (orgId: string, orgName: string) => {
		setScope({ type: "organization", orgId, orgName });
		setIsOpen(false);
	};

	const handleSelectGlobal = () => {
		setScope({ type: "global", orgId: null, orgName: null });
		setIsOpen(false);
	};

	return (
		<DropdownMenu open={isOpen} onOpenChange={handleOpenChange}>
			<DropdownMenuTrigger asChild>
				<Button variant="outline" className="gap-2">
					<Globe className="h-4 w-4" />
					<span className="hidden md:inline-block">
						{isGlobalScope ? "Global" : scope.orgName}
					</span>
					{isGlobalScope && (
						<Badge
							variant="secondary"
							className="ml-1 hidden lg:inline-flex"
						>
							Top-Level
						</Badge>
					)}
					<ChevronDown className="h-4 w-4" />
				</Button>
			</DropdownMenuTrigger>
			<DropdownMenuContent align="end" className="w-96">
				<DropdownMenuLabel>Organization Scope</DropdownMenuLabel>
				<DropdownMenuSeparator />

				{/* Global Option */}
				<DropdownMenuItem
					onClick={handleSelectGlobal}
					className={isGlobalScope ? "bg-accent" : ""}
				>
					<Globe className="mr-2 h-4 w-4" />
					<div className="flex flex-col flex-1">
						<span className="font-medium">Global</span>
						<span className="text-xs text-muted-foreground">
							Manage global forms and config
						</span>
					</div>
				</DropdownMenuItem>

				<DropdownMenuSeparator />

				{/* Search Box */}
				<div className="px-2 py-2">
					<div className="relative">
						<Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
						<Input
							placeholder="Search organizations..."
							value={searchQuery}
							onChange={(e) => setSearchQuery(e.target.value)}
							className="pl-8"
							onClick={(e) => e.stopPropagation()}
						/>
					</div>
				</div>

				<DropdownMenuSeparator />

				{/* Organizations List */}
				<div className="max-h-[400px] overflow-y-auto">
					<DropdownMenuLabel className="text-xs text-muted-foreground">
						Organizations ({filteredOrgs.length})
					</DropdownMenuLabel>

					{isLoading ? (
						<DropdownMenuItem disabled>
							Loading organizations...
						</DropdownMenuItem>
					) : filteredOrgs.length > 0 ? (
						filteredOrgs.map((org) => (
							<DropdownMenuItem
								key={org.id}
								onClick={() =>
									handleSelectOrg(org.id, org.name)
								}
								className={
									scope.orgId === org.id ? "bg-accent" : ""
								}
							>
								<Building2 className="mr-2 h-4 w-4 flex-shrink-0" />
								<div className="flex flex-col flex-1 min-w-0">
									<span className="font-medium truncate">
										{org.name}
									</span>
									<span className="text-xs text-muted-foreground font-mono truncate">
										{org.id}
									</span>
								</div>
							</DropdownMenuItem>
						))
					) : (
						<DropdownMenuItem disabled>
							{searchQuery
								? "No organizations match your search"
								: "No organizations found"}
						</DropdownMenuItem>
					)}
				</div>
			</DropdownMenuContent>
		</DropdownMenu>
	);
}
