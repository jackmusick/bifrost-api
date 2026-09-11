import { useState } from "react";
import {
	Filter,
	X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "@/components/ui/popover";
import {
	Command,
	CommandEmpty,
	CommandGroup,
	CommandInput,
	CommandItem,
	CommandList,
	CommandSeparator,
} from "@/components/ui/command";
import type { Organization } from "./types";

export interface FilterPopoverProps {
	typeFilter: string;
	setTypeFilter: (v: string) => void;
	orgFilter: string;
	setOrgFilter: (v: string) => void;
	accessFilter: string;
	setAccessFilter: (v: string) => void;
	usageFilter: string;
	setUsageFilter: (v: string) => void;
	organizations: Organization[];
	activeFilterCount: number;
	onClearFilters: () => void;
}

export function FilterPopover({
	typeFilter,
	setTypeFilter,
	orgFilter,
	setOrgFilter,
	accessFilter,
	setAccessFilter,
	usageFilter,
	setUsageFilter,
	organizations,
	activeFilterCount,
	onClearFilters,
}: FilterPopoverProps) {
	const [open, setOpen] = useState(false);

	const typeOptions = [
		{ value: "all", label: "All Types" },
		{ value: "workflow", label: "Workflows" },
		{ value: "form", label: "Forms" },
		{ value: "agent", label: "Agents" },
		{ value: "app", label: "Apps" },
	];

	const orgOptions = [
		{ value: "all", label: "All Organizations" },
		{ value: "global", label: "Global" },
		...organizations.map((org) => ({ value: org.id, label: org.name })),
	];

	const accessOptions = [
		{ value: "all", label: "All Access Levels" },
		{ value: "authenticated", label: "Everyone except external users" },
		{ value: "everyone", label: "Everyone" },
		{ value: "role_based", label: "Role-based" },
	];

	const usageOptions = [
		{ value: "all", label: "All Usage" },
		{ value: "unused", label: "Unused (0 refs)" },
		{ value: "in_use", label: "In Use" },
		{
			value: "related_mismatch",
			label: "Related scope/access mismatch",
		},
	];

	return (
		<Popover open={open} onOpenChange={setOpen}>
			<PopoverTrigger asChild>
				<Button type="button" variant="outline" className="min-h-11" aria-label={`Filters${activeFilterCount ? ` (${activeFilterCount} active)` : ""}`}>
					<Filter aria-hidden="true" className="size-4" />
					Filters
					{activeFilterCount > 0 && (
						<Badge
							variant="secondary"
							className="min-w-5 justify-center"
						>
							{activeFilterCount}
						</Badge>
					)}
				</Button>
			</PopoverTrigger>
			<PopoverContent aria-label="Entity filters" className="flex max-h-[var(--radix-popover-content-available-height)] w-[min(24rem,calc(100vw-2rem))] flex-col overflow-hidden p-0" align="start">
				<Command label="Search filters" className="min-h-0 flex-1">
					<CommandInput aria-label="Search filters" placeholder="Search filters…" />
					<CommandList className="min-h-0 max-h-[min(24rem,55dvh)] flex-1">
						<CommandGroup heading="Entity Type">
							{typeOptions.map((option) => (
								<CommandItem
									key={option.value}
									value={`type:${option.value}`}
									keywords={[option.label]}
									className="min-h-11 lg:min-h-11 whitespace-normal [overflow-wrap:anywhere]"
									data-checked={typeFilter === option.value}
									onSelect={() => setTypeFilter(option.value)}
								>
									<span className="min-w-0 flex-1">{option.label}</span>
									{typeFilter === option.value && <><span className="sr-only">Current filter</span></>}
								</CommandItem>
							))}
						</CommandGroup>
						<CommandSeparator />
						<CommandGroup heading="Organization">
							{orgOptions.map((option) => (
								<CommandItem
									key={option.value}
									value={`org:${option.value}`}
									keywords={[option.label]}
									className="min-h-11 lg:min-h-11 whitespace-normal [overflow-wrap:anywhere]"
									data-checked={orgFilter === option.value}
									onSelect={() => setOrgFilter(option.value)}
								>
									<span className="min-w-0 flex-1">{option.label}</span>
									{orgFilter === option.value && <><span className="sr-only">Current filter</span></>}
								</CommandItem>
							))}
						</CommandGroup>
						<CommandSeparator />
						<CommandGroup heading="Access Level">
							{accessOptions.map((option) => (
								<CommandItem
									key={option.value}
									value={`access:${option.value}`}
									keywords={[option.label]}
									className="min-h-11 lg:min-h-11 whitespace-normal [overflow-wrap:anywhere]"
									data-checked={accessFilter === option.value}
									onSelect={() => setAccessFilter(option.value)}
								>
									<span className="min-w-0 flex-1">{option.label}</span>
									{accessFilter === option.value && <><span className="sr-only">Current filter</span></>}
								</CommandItem>
							))}
						</CommandGroup>
						<CommandSeparator />
						<CommandGroup heading="Usage">
							<p className="px-2 pb-1 text-xs leading-5 text-muted-foreground">
								Related mismatch uses only relationships loaded
								in the expanded directory view.
							</p>
							{usageOptions.map((option) => (
								<CommandItem
									key={option.value}
									value={`usage:${option.value}`}
									keywords={[option.label]}
									className="min-h-11 lg:min-h-11 whitespace-normal [overflow-wrap:anywhere]"
									data-checked={usageFilter === option.value}
									onSelect={() => setUsageFilter(option.value)}
								>
									<span className="min-w-0 flex-1">{option.label}</span>
									{usageFilter === option.value && <><span className="sr-only">Current filter</span></>}
								</CommandItem>
							))}
						</CommandGroup>
						<CommandEmpty>No filters found.</CommandEmpty>
					</CommandList>
				</Command>
				{activeFilterCount > 0 && (
					<div className="shrink-0 p-2 border-t">
						<Button
							variant="ghost"
							size="sm"
							type="button"
							className="min-h-11 w-full"
							onClick={() => {
								onClearFilters();
								setOpen(false);
							}}
						>
							<X className="h-4 w-4 mr-2" />
							Clear all filters
						</Button>
					</div>
				)}
			</PopoverContent>
		</Popover>
	);
}
