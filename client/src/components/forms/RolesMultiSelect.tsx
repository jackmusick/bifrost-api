/**
 * Roles Multi-Select Component
 *
 * Searchable multi-select for picking N roles. Mirrors OrganizationSelect's
 * Popover + Command pattern, with checkmarks instead of a single selected
 * radio. Scales past long role lists (you can type to filter).
 *
 * Used by BulkReplaceRolesDialog. Other "pick roles" dialogs in the codebase
 * are migration candidates.
 */

import { useMemo, useState } from "react";
import { ChevronsUpDown, Shield } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
	Command,
	CommandEmpty,
	CommandGroup,
	CommandInput,
	CommandItem,
	CommandList,
} from "@/components/ui/command";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "@/components/ui/popover";
import { useRoles } from "@/hooks/useRoles";

export interface RolesMultiSelectProps {
	/** Currently selected role ids. */
	value: string[];
	/** Fired with the new selection on every change. */
	onChange: (next: string[]) => void;
	disabled?: boolean;
	placeholder?: string;
	triggerClassName?: string;
	contentClassName?: string;
}

export function RolesMultiSelect({
	value,
	onChange,
	disabled = false,
	placeholder = "Select roles...",
	triggerClassName,
	contentClassName,
}: RolesMultiSelectProps) {
	const [open, setOpen] = useState(false);
	const { data: roles, isLoading, isError, isFetching, refetch } = useRoles();
	const blocked = disabled || isLoading;
	if (blocked && open) setOpen(false);

	const selectedSet = useMemo(() => new Set(value), [value]);

	const toggle = (id: string) => {
		if (blocked) return;
		const next = new Set(selectedSet);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		onChange(Array.from(next));
	};

	const summary =
		value.length === 0
			? placeholder
			: value.length === 1
				? (roles?.find((r) => r.id === value[0])?.name ?? "1 selected")
				: `${value.length} selected`;

	return (
		<Popover open={open && !blocked} onOpenChange={setOpen}>
			<PopoverTrigger asChild>
				<Button
					type="button"
					variant="outline"
					role="combobox"
					aria-expanded={open && !blocked}
					aria-label="Select roles"
					className={cn(
						"h-auto min-h-11 w-full justify-between whitespace-normal text-left font-normal",
						triggerClassName,
					)}
					disabled={blocked}
				>
					<span className="flex items-center gap-2 min-w-0">
						<Shield className="h-4 w-4 shrink-0 text-muted-foreground" />
						<span className="[overflow-wrap:anywhere]">
							{isLoading ? "Loading roles…" : summary}
						</span>
					</span>
					<ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
				</Button>
			</PopoverTrigger>
			<PopoverContent variant="picker"
				className={cn(
					"p-0",
					contentClassName,
				)}
				align="start"
			>
				{isError && (
					<div className="space-y-2 border-b p-3">
						<p
							role="alert"
							className="text-sm leading-6 text-destructive"
						>
							{roles
								? "Could not refresh roles. Showing the last loaded list."
								: "Could not load roles. Your selection is preserved."}
						</p>
						<Button
							type="button"
							variant="outline"
							className="min-h-11"
							disabled={isFetching || disabled}
							onClick={() => void refetch()}
						>
							Retry roles
						</Button>
					</div>
				)}
				<Command>
					<CommandInput
						placeholder="Search roles..."
						aria-label="Search roles"
					/>
					<CommandList className="max-h-72 overflow-y-auto">
						{!isError && (
							<CommandEmpty>No roles found.</CommandEmpty>
						)}
						<CommandGroup>
							{(roles ?? []).map((role) => {
								const selected = selectedSet.has(role.id);
								return (
									<CommandItem
										key={role.id}
										value={role.id}
										keywords={[
											role.name,
											role.description ?? "",
										].filter(Boolean)}
										disabled={blocked}
										className="min-h-11 lg:min-h-11"
										data-checked={selected}
										onSelect={() => toggle(role.id)}
									>
										<div className="flex flex-1 flex-col min-w-0 [overflow-wrap:anywhere]">
											<span className="font-medium">
												{role.name}
											</span>
											{selected && (
												<span className="sr-only">
													Selected
												</span>
											)}
											{role.description && (
												<span className="text-sm leading-6 text-muted-foreground">
													{role.description}
												</span>
											)}
										</div>
									</CommandItem>
								);
							})}
						</CommandGroup>
					</CommandList>
				</Command>
			</PopoverContent>
		</Popover>
	);
}
