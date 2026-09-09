import * as React from "react";
import { ChevronsUpDown, Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";
import { SelectionChip } from "@/components/ui/selection-chip";
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
import type { ComboboxOption } from "@/components/ui/combobox";

interface MultiComboboxProps {
	options: ComboboxOption[];
	value?: string[];
	onValueChange?: (value: string[]) => void;
	placeholder?: string;
	searchPlaceholder?: string;
	emptyText?: string;
	disabled?: boolean;
	isLoading?: boolean;
	className?: string;
	id?: string;
}

export function MultiCombobox({
	options,
	value = [],
	onValueChange,
	placeholder = "Select options...",
	searchPlaceholder = "Search...",
	emptyText = "No option found.",
	disabled = false,
	isLoading = false,
	className,
	id,
}: MultiComboboxProps) {
	const [open, setOpen] = React.useState(false);

	const selectedSet = React.useMemo(() => new Set(value), [value]);
	const selectedOptions = React.useMemo(
		() =>
			value.map(
				(v) =>
					options.find((o) => o.value === v) ?? {
						value: v,
						label: v,
					},
			),
		[options, value],
	);

	const toggle = (optionValue: string) => {
		if (selectedSet.has(optionValue)) {
			onValueChange?.(value.filter((v) => v !== optionValue));
		} else {
			onValueChange?.([...value, optionValue]);
		}
	};

	const triggerRef = React.useRef<HTMLButtonElement>(null);
	const blocked = disabled || isLoading;
	if (blocked && open) setOpen(false);
	const listId = React.useId();
	return (
		<div className="min-w-0 space-y-2">
			<Popover open={open && !blocked} onOpenChange={setOpen}>
				<PopoverTrigger asChild>
					<Button
						type="button"
						ref={triggerRef}
						id={id}
						variant="outline"
						role="combobox"
						aria-expanded={open && !blocked}
						aria-controls={open && !blocked ? listId : undefined}
						disabled={blocked}
						className={cn(
							"h-auto min-h-11 w-full justify-between whitespace-normal text-left font-normal",
							className,
						)}
					>
						<span className="min-w-0 [overflow-wrap:anywhere]">
							{isLoading
								? "Loading..."
								: selectedOptions.length
									? `${selectedOptions.length} selected`
									: placeholder}
						</span>
						{isLoading ? (
							<Loader2 className="h-4 w-4 shrink-0 motion-safe:animate-spin" />
						) : (
							<ChevronsUpDown className="h-4 w-4 shrink-0 text-muted-foreground" />
						)}
					</Button>
				</PopoverTrigger>
				<PopoverContent variant="picker"
					className="p-0"
					align="start"
					aria-label="Select options"
				>
					<Command>
						<CommandInput
							placeholder={searchPlaceholder}
							aria-label={searchPlaceholder}
						/>
						<CommandList
							id={listId}
							className="max-h-60 overflow-y-auto"
						>
							<CommandEmpty>{emptyText}</CommandEmpty>
							<CommandGroup>
								{options.map((option) => (
									<CommandItem
										key={option.value}
										value={option.value}
										keywords={[option.label]}
										data-checked={selectedSet.has(
											option.value,
										)}
										disabled={blocked}
										className="min-h-11 lg:min-h-11"
										onSelect={() => {
											if (!blocked) toggle(option.value);
										}}
									>
										<div className="min-w-0 flex-1 space-y-1 [overflow-wrap:anywhere]">
											<span className="font-medium">
												{option.label}
											</span>
											{selectedSet.has(option.value) && (
												<span className="sr-only">
													Selected
												</span>
											)}
											{option.description && (
												<p className="text-sm leading-6 text-muted-foreground">
													{option.description}
												</p>
											)}
										</div>
									</CommandItem>
								))}
							</CommandGroup>
						</CommandList>
					</Command>
				</PopoverContent>
			</Popover>
			{selectedOptions.length > 0 && (
				<ul
					aria-label="Selected options"
					className="flex min-w-0 flex-wrap gap-2"
				>
					{selectedOptions.map((option) => (
						<SelectedOption
							key={option.value}
							label={option.label}
							disabled={blocked}
							onRemove={() => {
								if (blocked) return;
								onValueChange?.(
									value.filter((v) => v !== option.value),
								);
								triggerRef.current?.focus();
							}}
						/>
					))}
				</ul>
			)}
		</div>
	);
}

function SelectedOption({
	label,
	disabled,
	onRemove,
}: {
	label: string;
	disabled: boolean;
	onRemove: () => void;
}) {
	return (
		<li className="min-w-0 max-w-full">
			<SelectionChip
				label={label}
				disabled={disabled}
				onRemove={onRemove}
			/>
		</li>
	);
}
