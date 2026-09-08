import { useId, useRef } from "react";
import { Search, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface EditorSearchFormProps {
	query: string;
	caseSensitive: boolean;
	useRegex: boolean;
	isSearching: boolean;
	onQueryChange: (query: string) => void;
	onCaseSensitiveChange: (value: boolean) => void;
	onUseRegexChange: (value: boolean) => void;
	onSearch: () => void;
	onClear: () => void;
}
export function EditorSearchForm(props: EditorSearchFormProps) {
	const id = useId();
	const inputRef = useRef<HTMLInputElement>(null);
	return (
		<form
			aria-label="Search file contents"
			className="space-y-3 border-b p-3"
			onSubmit={(event) => {
				event.preventDefault();
				if (!props.isSearching && props.query.trim()) props.onSearch();
			}}
		>
			<Label htmlFor={id}>Search file contents</Label>
			<Input
				ref={inputRef}
				id={id}
				value={props.query}
				onChange={(event) => props.onQueryChange(event.target.value)}
				disabled={props.isSearching}
				placeholder="Find text in files"
				className="min-h-11"
				autoCapitalize="none"
				autoCorrect="off"
				spellCheck={false}
			/>
			<div className="flex flex-wrap gap-2">
				<Button
					type="button"
					variant={props.caseSensitive ? "secondary" : "outline"}
					aria-pressed={props.caseSensitive}
					onClick={() =>
						props.onCaseSensitiveChange(!props.caseSensitive)
					}
					disabled={props.isSearching}
					className="min-h-11 h-auto whitespace-normal px-3"
				>
					Match case
				</Button>
				<Button
					type="button"
					variant={props.useRegex ? "secondary" : "outline"}
					aria-pressed={props.useRegex}
					onClick={() => props.onUseRegexChange(!props.useRegex)}
					disabled={props.isSearching}
					className="min-h-11 h-auto whitespace-normal px-3"
				>
					Use regex
				</Button>
			</div>
			<div className="flex gap-2">
				<Button
					type="submit"
					disabled={props.isSearching || !props.query.trim()}
					className="min-h-11 flex-1"
				>
					{props.isSearching ? (
						<Loader2 className="size-4 animate-spin motion-reduce:animate-none" />
					) : (
						<Search className="size-4" />
					)}
					Search
				</Button>
				<Button
					type="button"
					variant="outline"
					size="icon"
					aria-label="Clear search"
					disabled={!props.query && !props.isSearching}
					className="size-11 shrink-0"
					onClick={() => {
						props.onClear();
						requestAnimationFrame(() => inputRef.current?.focus());
					}}
				>
					<X className="size-4" />
				</Button>
			</div>
		</form>
	);
}
