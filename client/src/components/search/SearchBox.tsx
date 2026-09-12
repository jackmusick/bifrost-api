import { Search, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface SearchBoxProps {
	"aria-label"?: string;
	value?: string;
	onChange: (value: string) => void;
	placeholder?: string;
	debounceMs?: number;
	className?: string;
}

export function SearchBox({
	value = "",
	onChange,
	placeholder = "Search...",
	debounceMs = 300,
	className = "",
	"aria-label": ariaLabel,
}: SearchBoxProps) {
	const inputRef = useRef<HTMLInputElement>(null);
	const [localValue, setLocalValue] = useState(value);

	// Sync local value when controlled `value` prop changes (e.g. parent
	// reset). Adjust during render rather than in an effect — see
	// https://react.dev/learn/you-might-not-need-an-effect#adjusting-some-state-when-a-prop-changes
	const [prevValue, setPrevValue] = useState(value);
	if (prevValue !== value) {
		setPrevValue(value);
		setLocalValue(value);
	}

	// Debounce the onChange callback
	useEffect(() => {
		const timer = setTimeout(() => {
			if (localValue !== value) {
				onChange(localValue);
			}
		}, debounceMs);

		return () => clearTimeout(timer);
	}, [localValue, debounceMs, onChange, value]);

	const handleClear = () => {
		setLocalValue("");
		onChange("");
		inputRef.current?.focus();
	};

	return (
		<div className={`relative ${className}`}>
			<Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
			<Input
				ref={inputRef}
				aria-label={ariaLabel ?? placeholder}
				type="text"
				value={localValue}
				onChange={(e) => setLocalValue(e.target.value)}
				placeholder={placeholder}
				className="h-11 pl-9 pr-12 lg:h-10 lg:pr-9"
			/>
			{localValue && (
				<Button
					variant="ghost"
					size="sm"
					onClick={handleClear}
					className="absolute inset-y-0 right-0 my-auto h-11 w-11 p-0 lg:right-1 lg:h-7 lg:w-7"
				>
					<X className="h-4 w-4" />
					<span className="sr-only">Clear search</span>
				</Button>
			)}
		</div>
	);
}
