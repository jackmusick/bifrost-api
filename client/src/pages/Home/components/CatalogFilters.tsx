import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import type { HomeResource } from "@/services/home";

export function CatalogFilters({
	value,
	resources,
	onChange,
}: {
	value: string;
	resources: HomeResource[];
	onChange: (value: string) => void;
}) {
	return (
		<Select value={value} onValueChange={onChange}>
			<SelectTrigger aria-label="Resource type" className="w-32">
				<SelectValue>
					{(
						{
							all: "All types",
							app: "Apps",
							form: "Forms",
							agent: "Agents",
						} as Record<string, string>
					)[value] ?? "All types"}
				</SelectValue>
			</SelectTrigger>
			<SelectContent>
				{[
					{ value: "all", label: "All types" },
					{ value: "app", label: "Apps" },
					{ value: "form", label: "Forms" },
					{ value: "agent", label: "Agents" },
				].map((category) => (
					<SelectItem key={category.value} value={category.value}>
						{category.label}
						<span className="ml-2 text-muted-foreground">
							{category.value === "all"
								? resources.length
								: resources.filter(
										(r) => r.kind === category.value,
									).length}
						</span>
					</SelectItem>
				))}
			</SelectContent>
		</Select>
	);
}
