import { useQuery } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SolutionManagedBadge } from "@/components/solutions/SolutionManagedBadge";
import { effectiveAccess } from "@/services/filePolicies";
import { InlineLoader } from "./InlineLoader";

interface EffectiveAccessPanelProps {
	location: string;
	scope: string | null;
	path: string | null;
	readOnly?: boolean;
	managedBySolution?: boolean;
	solutionId?: string | null;
	onOpenTest: () => void;
	onManagePolicy: () => void;
}

export function EffectiveAccessPanel({
	location,
	scope,
	path,
	readOnly = false,
	managedBySolution = false,
	solutionId = null,
	onOpenTest,
	onManagePolicy,
}: EffectiveAccessPanelProps) {
	const accessQuery = useQuery({
		queryKey: ["effective-access", location, scope, path],
		queryFn: () => effectiveAccess(location, path ?? "", scope),
		enabled: path !== null,
		retry: false,
	});
	const policies = accessQuery.data ?? [];
	const error = accessQuery.isError;
	const loading = accessQuery.isLoading || accessQuery.isFetching;

	return (
		<section
			aria-label="Effective access"
			className="flex h-full min-h-0 min-w-0 flex-col"
		>
			<div className="flex shrink-0 flex-col gap-3 border-b p-3">
				<div className="flex min-w-0 flex-wrap items-center gap-2">
					<ShieldCheck className="h-4 w-4 text-muted-foreground" />
					<h2 className="min-w-0 text-sm font-semibold leading-5">
						Effective Access
					</h2>
					{managedBySolution && (
						<SolutionManagedBadge
							solutionId={solutionId ?? undefined}
						/>
					)}
				</div>
				<div className="flex flex-wrap gap-2">
					{!readOnly && (
						<Button
							type="button"
							variant="outline"
							size="default"
							className="min-h-11"
							disabled={path === null}
							onClick={onManagePolicy}
						>
							Manage policy
						</Button>
					)}
					<Button
						type="button"
						size="default"
						className="min-h-11"
						onClick={onOpenTest}
						disabled={path === null}
					>
						Test access
					</Button>
				</div>
			</div>
			<div className="min-h-0 min-w-0 flex-1 overflow-auto p-3 text-sm">
				{path === null && (
					<p className="[overflow-wrap:anywhere] text-muted-foreground">
						Select an item to see what governs it.
					</p>
				)}
				{loading && <InlineLoader label="Resolving…" />}
				{error && (
					<div role="alert" className="space-y-2">
						<p className="[overflow-wrap:anywhere] text-destructive">
							Couldn’t resolve access for this item.
						</p>
						<Button
							type="button"
							variant="outline"
							size="default"
							className="min-h-11"
							disabled={accessQuery.isFetching}
							onClick={() => void accessQuery.refetch()}
						>
							Retry access
						</Button>
					</div>
				)}
				{path !== null &&
					!loading &&
					!error &&
					policies.length === 0 && (
						<p className="[overflow-wrap:anywhere] text-muted-foreground">
							No policy governs this path (default deny).
						</p>
					)}
				<ul className="space-y-2">
					{policies.map((policy, index) => (
						<li
							key={
								policy.id ?? `${policy.location}:${policy.path}`
							}
							className="rounded-[var(--bf-radius-surface)] border p-3"
						>
							<div className="flex flex-wrap items-start justify-between gap-2">
								<span className="min-w-0 [overflow-wrap:anywhere] font-mono text-xs">
									{policy.path || "(root)"}
								</span>
								{index === 0 && (
									<Badge variant="secondary">winning</Badge>
								)}
							</div>
							<ul className="mt-1 space-y-0.5">
								{policy.policies.policies.map((rule, i) =>
									"$ref" in rule ? (
										<li
											key={rule.$ref}
											className="[overflow-wrap:anywhere] text-muted-foreground"
										>
											<span className="[overflow-wrap:anywhere] font-mono font-medium text-foreground">
												ref: {rule.$ref}
											</span>
										</li>
									) : (
										<li
											key={rule.name ?? i}
											className="[overflow-wrap:anywhere] text-muted-foreground"
										>
											<span className="[overflow-wrap:anywhere] font-medium text-foreground">
												{rule.name}
											</span>{" "}
											<span className="[overflow-wrap:anywhere]">
												→ {rule.actions.join(", ")}
											</span>
										</li>
									),
								)}
							</ul>
						</li>
					))}
				</ul>
			</div>
		</section>
	);
}
