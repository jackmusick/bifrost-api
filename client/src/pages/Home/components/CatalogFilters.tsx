import { AppWindow, Bot, FileInput, LayoutGrid } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { HomeResource } from "@/services/home";

const categories = [
	{ value: "all", label: "All", icon: LayoutGrid },
	{ value: "app", label: "Apps", icon: AppWindow },
	{ value: "form", label: "Forms", icon: FileInput },
	{ value: "agent", label: "Agents", icon: Bot },
];

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
		<div
			role="group"
			aria-label="Resource categories"
			className="grid grid-cols-4 gap-2 sm:flex sm:gap-3"
		>
			{categories.map(({ value: category, label, icon: Icon }) => (
				<Button
					key={category}
					variant="outline"
					aria-label={label}
					aria-pressed={value === category}
					className={`h-auto min-h-12 min-w-0 flex-col gap-1 px-2 py-2 sm:min-w-32 sm:flex-row sm:gap-3 sm:px-4 ${value === category ? "border-primary bg-primary/10 text-primary hover:bg-primary/15" : ""}`}
					onClick={() => onChange(category)}
				>
					<Icon className="hidden size-4 shrink-0 sm:block" />
					<span>{label}</span>
					<span className="text-xs tabular-nums opacity-80">
						{category === "all"
							? resources.length
							: resources.filter(
									(resource) => resource.kind === category,
								).length}
					</span>
				</Button>
			))}
		</div>
	);
}
