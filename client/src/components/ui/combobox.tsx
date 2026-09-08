import * as React from "react";
import { ChevronsUpDown, Loader2 } from "lucide-react";

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

export interface ComboboxOption {
	value: string;
	label: string;
	description?: string;
}

interface ComboboxProps {
	"aria-describedby"?: string;
	"aria-invalid"?: React.AriaAttributes["aria-invalid"];
	options: ComboboxOption[];
	value?: string;
	onValueChange?: (value: string) => void;
	placeholder?: string;
	searchPlaceholder?: string;
	emptyText?: string;
	disabled?: boolean;
	isLoading?: boolean;
	className?: string;
	id?: string;
}

export function Combobox({
	options,
	value,
	onValueChange,
	placeholder = "Select an option...",
	searchPlaceholder = "Search...",
	emptyText = "No option found.",
	disabled = false,
	isLoading = false,
	className,
	id,
	"aria-describedby": describedBy,
	"aria-invalid": invalid,
}: ComboboxProps) {
	const [open, setOpen] = React.useState(false);
	const filter = React.useCallback(
		(value: string, search: string, keywords?: string[]) => {
			const terms = search.toLocaleLowerCase().trim().split(/\s+/);
			const searchable = [value, ...(keywords ?? [])]
				.join(" ")
				.toLocaleLowerCase();
			return terms.every((term) => searchable.includes(term)) ? 1 : 0;
		},
		[],
	);

	const selectedOption = options.find((option) => option.value === value);

	return (
		<Popover open={open} onOpenChange={setOpen}>
			<PopoverTrigger asChild>
				<Button
					id={id}
					variant="outline"
					role="combobox"
					aria-expanded={open}
					aria-describedby={describedBy}
					aria-invalid={invalid}
					className={cn(
						"h-auto min-h-11 w-full min-w-0 justify-between py-2 font-normal sm:min-h-10",
						className,
					)}
					disabled={disabled || isLoading}
				>
					{isLoading ? (
						<>
							<Loader2
								aria-hidden="true"
								className="mr-2 h-4 w-4 animate-spin motion-reduce:animate-none"
							/>
							<span className="text-muted-foreground">
								Loading...
							</span>
						</>
					) : (
						<>
							<span
								className={cn(
									"min-w-0 whitespace-normal text-left [overflow-wrap:anywhere]",
									!value && "text-muted-foreground",
								)}
							>
								{selectedOption?.label ?? (value || placeholder)}
							</span>
							<ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
						</>
					)}
				</Button>
			</PopoverTrigger>
			<PopoverContent
				className="max-h-[var(--radix-popover-content-available-height)] w-[var(--radix-popover-trigger-width)] max-w-[calc(100vw-2rem)] overflow-hidden p-0"
				align="start"
			>
				<Command
					filter={filter}
					label={searchPlaceholder}
					className="min-h-0"
				>
					<CommandInput
						aria-label={searchPlaceholder}
						placeholder={searchPlaceholder}
					/>
					<CommandList className="min-h-0 max-h-60 overflow-y-auto">
						<CommandEmpty>{emptyText}</CommandEmpty>
						<CommandGroup>
							{options.map((option) => (
								<CommandItem
									key={option.value}
									value={option.value}
									className="min-h-11"
									keywords={[option.label]}
									data-checked={value === option.value}
									onSelect={() => {
										onValueChange?.(
											option.value === value
												? ""
												: option.value,
										);
										setOpen(false);
									}}
								>
									<div className="flex min-w-0 flex-1 flex-col [overflow-wrap:anywhere]">
										<span className="font-medium">
											{option.label}
										</span>
										{option.description && (
											<span className="text-xs text-muted-foreground">
												{option.description}
											</span>
										)}
									</div>
								</CommandItem>
							))}
						</CommandGroup>
					</CommandList>
				</Command>
			</PopoverContent>
		</Popover>
	);
}
