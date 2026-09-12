import { useState } from "react";
import { Folder } from "lucide-react";
import { getIcon } from "@/lib/icons";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const icons = [
	"folder",
	"folder-open",
	"briefcase-business",
	"building-2",
	"users",
	"user-round-plus",
	"heart",
	"star",
	"bookmark",
	"rocket",
	"zap",
	"workflow",
	"bot",
	"message-square",
	"app-window",
	"file-input",
	"shield-check",
	"key-round",
	"lock-keyhole",
	"network",
	"server",
	"database",
	"hard-drive",
	"monitor",
	"laptop",
	"wrench",
	"settings",
	"mail",
	"calendar",
	"clock",
	"clipboard-list",
	"list-checks",
	"chart-no-axes-combined",
	"graduation-cap",
	"headset",
	"globe",
	"cloud",
	"package",
	"boxes",
	"code",
	"terminal",
	"sparkles",
];

export function CollectionIconPicker({
	value,
	onChange,
}: {
	value: string;
	onChange: (icon: string) => void;
}) {
	const [search, setSearch] = useState("");
	const matches = icons.filter((icon) =>
		icon.replaceAll("-", " ").includes(search.toLowerCase().trim()),
	);
	return (
		<fieldset className="min-w-0 space-y-3">
			<legend className="text-sm font-medium">Collection icon</legend>
			<Input
				aria-label="Search collection icons"
				placeholder="Search icons…"
				value={search}
				onChange={(event) => setSearch(event.target.value)}
			/>
			<div
				className="flex flex-wrap gap-1 p-1"
				aria-label="Available icons"
			>
				{matches.map((name) => {
					const Icon = getIcon(name, Folder);
					return (
						<Button
							key={name}
							type="button"
							variant="ghost"
							size="icon"
							aria-label={name.replaceAll("-", " ")}
							aria-pressed={value === name}
							onClick={() => onChange(name)}
							className={cn(
								"size-11",
								value === name &&
									"bg-primary/10 text-primary ring-1 ring-inset ring-primary",
							)}
						>
							<Icon className="size-5" />
						</Button>
					);
				})}
				{matches.length === 0 && (
					<p className="py-2 text-sm text-muted-foreground">
						No matching icons.
					</p>
				)}
			</div>
		</fieldset>
	);
}
