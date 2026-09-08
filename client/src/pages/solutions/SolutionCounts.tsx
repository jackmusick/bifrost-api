import {
	Workflow,
	AppWindow,
	FileCode,
	Bot,
	Database,
	KeyRound,
	FolderOpen,
} from "lucide-react";
import type { Solution } from "@/services/solutions";
type SolutionCountKey =
	"workflows" | "apps" | "forms" | "agents" | "tables" | "claims" | "files";

const COUNT_ITEMS: {
	key: SolutionCountKey;
	label: string;
	shortLabel: string;
	Icon: typeof Workflow;
	className: string;
}[] = [
	{
		key: "workflows",
		label: "Workflows",
		shortLabel: "Flows",
		Icon: Workflow,
		className:
			"border-blue-500/30 bg-blue-500/10 text-blue-700 dark:text-blue-300",
	},
	{
		key: "apps",
		label: "Apps",
		shortLabel: "Apps",
		Icon: AppWindow,
		className:
			"border-indigo-500/30 bg-indigo-500/10 text-indigo-700 dark:text-indigo-300",
	},
	{
		key: "forms",
		label: "Forms",
		shortLabel: "Forms",
		Icon: FileCode,
		className:
			"border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
	},
	{
		key: "agents",
		label: "Agents",
		shortLabel: "Agents",
		Icon: Bot,
		className:
			"border-violet-500/30 bg-violet-500/10 text-violet-700 dark:text-violet-300",
	},
	{
		key: "tables",
		label: "Tables",
		shortLabel: "Tables",
		Icon: Database,
		className:
			"border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300",
	},
	{
		key: "claims",
		label: "Custom Claims",
		shortLabel: "Claims",
		Icon: KeyRound,
		className:
			"border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-300",
	},
	{
		key: "files",
		label: "Files",
		shortLabel: "Files",
		Icon: FolderOpen,
		className:
			"border-cyan-500/30 bg-cyan-500/10 text-cyan-700 dark:text-cyan-300",
	},
];

function solutionEntityCounts(
	sol: Solution,
): Partial<Record<SolutionCountKey, number>> {
	return (
		(
			sol as Solution & {
				entity_counts?: Partial<Record<SolutionCountKey, number>>;
			}
		).entity_counts ?? {}
	);
}

function visibleCountItems(sol: Solution) {
	const counts = solutionEntityCounts(sol);
	return COUNT_ITEMS.map((item) => ({
		...item,
		count: counts[item.key] ?? 0,
	})).filter((item) => item.count > 0);
}

export function SolutionCounts({ solution }: { solution: Solution }) {
	const items = visibleCountItems(solution);
	if (!items.length)
		return (
			<span className="text-xs text-muted-foreground">No contents</span>
		);
	return items.map(({ key, label, Icon, count, className }) => (
		<span
			key={key}
			data-testid={`solution-count-${key}`}
			className={`inline-flex min-h-6 items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${className}`}
		>
			<Icon aria-hidden="true" className="size-3 shrink-0" />
			<span className="tabular-nums">{count}</span>
			<span>{label}</span>
		</span>
	));
}
