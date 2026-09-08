import { useQuery } from "@tanstack/react-query";
import { Pencil, Trash2 } from "lucide-react";
import { RecordActionsMenu } from "@/components/common/RecordActionsMenu";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
	DataTable,
	DataTableBody,
	DataTableCell,
	DataTableHead,
	DataTableHeader,
	DataTableRow,
} from "@/components/ui/data-table";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import {
	listFilePolicies,
	type FilePolicy,
	type PolicyRuleRef,
} from "@/services/filePolicies";
import { InlineLoader } from "./InlineLoader";

interface PoliciesViewProps {
	scope: string | null;
	/** Bump to force a refetch after a policy mutation elsewhere. */
	refreshKey: number;
	onEdit: (policy: FilePolicy) => void;
	onDelete: (policy: FilePolicy) => void;
}

/**
 * Flat list of every file policy in the current scope — the "manage all
 * policies" surface the per-item "Manage policy" modal can't provide. Lists
 * across all locations; each row opens the policy editor for that exact
 * (location, path).
 */
export function PoliciesView({
	scope,
	refreshKey,
	onEdit,
	onDelete,
}: PoliciesViewProps) {
	const isCompactLayout = useMediaQuery("(max-width: 1023px)");
	const policiesQuery = useQuery({
		queryKey: ["file-policies", scope, refreshKey],
		queryFn: () => listFilePolicies({ scope: scope ?? undefined }),
		retry: false,
	});
	const policies = policiesQuery.data?.policies ?? [];
	const hasData = policiesQuery.data !== undefined;
	const showInitialLoading = policiesQuery.isPending && !hasData;
	const showEmptyState =
		!showInitialLoading && !policiesQuery.isError && policies.length === 0;
	const showError = policiesQuery.isError && !hasData;
	const showTransientError = policiesQuery.isError && hasData;

	type PolicyRule = FilePolicy["policies"]["policies"][number];

	const formatPath = (path: string) =>
		path ? (path.startsWith("/") ? path : `/${path}`) : "/";
	const formatIdentity = (policy: FilePolicy) =>
		`${policy.location}${formatPath(policy.path)}`;
	const isPolicyRuleRef = (rule: PolicyRule): rule is PolicyRuleRef =>
		"$ref" in rule;
	const renderRule = (rule: PolicyRule, index: number) => {
		const key = isPolicyRuleRef(rule) ? rule.$ref : `${rule.name}:${index}`;
		return (
			<Badge
				key={key}
				variant="outline"
				className="h-auto max-w-full items-start whitespace-normal [overflow-wrap:anywhere] rounded-[var(--bf-radius-control)] px-2 py-1 text-left leading-5"
			>
				{isPolicyRuleRef(rule) ? `ref:${rule.$ref}` : rule.name}
			</Badge>
		);
	};

	const renderActions = (policy: FilePolicy) => (
		<RecordActionsMenu label={`Policy ${formatIdentity(policy)} actions`}>
			<DropdownMenuItem
				className="min-h-11"
				onSelect={() => onEdit(policy)}
			>
				<Pencil aria-hidden="true" className="size-4" />
				Edit
			</DropdownMenuItem>
			<DropdownMenuItem
				variant="destructive"
				className="min-h-11"
				onSelect={() => onDelete(policy)}
			>
				<Trash2 aria-hidden="true" className="size-4" />
				Delete
			</DropdownMenuItem>
		</RecordActionsMenu>
	);

	const renderIdentity = (policy: FilePolicy) => (
		<button
			type="button"
			className="min-h-11 min-w-0 text-left rounded-[var(--bf-radius-control)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
			onClick={(event) => {
				event.stopPropagation();
				onEdit(policy);
			}}
			aria-label={`Edit policy for ${formatIdentity(policy)}`}
		>
			<span className="block text-sm font-semibold leading-6 [overflow-wrap:anywhere]">
				{policy.location}
			</span>
			<span className="block font-mono text-xs text-muted-foreground [overflow-wrap:anywhere]">
				{formatPath(policy.path)}
			</span>
		</button>
	);

	const renderMobilePolicy = (policy: FilePolicy) => (
		<li key={policy.id ?? `${policy.location}:${policy.path}`}>
			<Card className="rounded-[var(--bf-radius-surface)] border-border/70 bg-card py-0">
				<CardContent className="space-y-4 p-4">
					<div className="flex items-start justify-between gap-3">
						{renderIdentity(policy)}
						<div className="shrink-0">{renderActions(policy)}</div>
					</div>
					<div className="space-y-2">
						<p className="text-xs font-medium text-muted-foreground">
							Rules
						</p>
						<div className="flex flex-wrap gap-1.5">
							{policy.policies.policies.length === 0 ? (
								<span className="text-xs text-muted-foreground">
									No rules
								</span>
							) : (
								policy.policies.policies.map(renderRule)
							)}
						</div>
					</div>
				</CardContent>
			</Card>
		</li>
	);

	const renderDesktopPolicy = (policy: FilePolicy) => (
		<DataTableRow
			key={policy.id ?? `${policy.location}:${policy.path}`}
			clickable
			onClick={() => onEdit(policy)}
		>
			<DataTableCell className="w-[18rem] max-w-[18rem] align-middle">
				{renderIdentity(policy)}
			</DataTableCell>
			<DataTableCell className="align-middle">
				<div className="flex flex-wrap gap-1.5">
					{policy.policies.policies.length === 0 ? (
						<span className="text-xs text-muted-foreground">
							No rules
						</span>
					) : (
						policy.policies.policies.map(renderRule)
					)}
				</div>
			</DataTableCell>
			<DataTableCell className="w-px whitespace-nowrap align-middle">
				{renderActions(policy)}
			</DataTableCell>
		</DataTableRow>
	);

	return (
		<div className="h-full min-h-0 overflow-auto">
			{showInitialLoading ? (
				<InlineLoader className="p-4" />
			) : showError ? (
				<Alert
					variant="destructive"
					className="mx-4 my-4 w-[calc(100%-2rem)] rounded-[var(--bf-radius-surface)]"
				>
					<AlertTitle>File policies could not be loaded</AlertTitle>
					<AlertDescription>
						<p>Try again to load the policies for this scope.</p>
						<Button
							type="button"
							variant="outline"
							className="mt-3 min-h-11"
							onClick={() => void policiesQuery.refetch()}
						>
							Retry policies
						</Button>
					</AlertDescription>
				</Alert>
			) : showEmptyState ? (
				<p className="p-4 text-sm text-muted-foreground">
					No policies in this scope yet.
				</p>
			) : (
				<>
					{showTransientError && (
						<Alert
							variant="destructive"
							className="mx-4 my-4 w-[calc(100%-2rem)] rounded-[var(--bf-radius-surface)]"
						>
							<AlertTitle>
								File policies could not be refreshed
							</AlertTitle>
							<AlertDescription>
								<p>
									The current list is still shown, but the
									latest scope refresh failed.
								</p>
								<Button
									type="button"
									variant="outline"
									className="mt-3 min-h-11"
									onClick={() => void policiesQuery.refetch()}
								>
									Retry policies
								</Button>
							</AlertDescription>
						</Alert>
					)}
					{isCompactLayout ? (
						<ul className="space-y-3 p-4">
							{policies.map(renderMobilePolicy)}
						</ul>
					) : (
						<DataTable>
							<DataTableHeader>
								<DataTableRow>
									<DataTableHead className="w-px whitespace-nowrap">
										Policy
									</DataTableHead>
									<DataTableHead>Rules</DataTableHead>
									<DataTableHead className="w-px whitespace-nowrap text-right">
										Actions
									</DataTableHead>
								</DataTableRow>
							</DataTableHeader>
							<DataTableBody>
								{policies.map(renderDesktopPolicy)}
							</DataTableBody>
						</DataTable>
					)}
				</>
			)}
		</div>
	);
}
