import { Lock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { PolicyRuleActions } from "./PolicyRuleActions";
import type { PolicyRule } from "@/services/policyRules";

interface PolicyRuleSurfaceProps {
	rule: PolicyRule;
	onEdit: () => void;
	onDelete: () => void;
}

export function PolicyRuleSurface({
	rule,
	onEdit,
	onDelete,
}: PolicyRuleSurfaceProps) {
	return (
		<article
			data-testid="policy-rule-card"
			className="space-y-3 rounded-[var(--bf-radius-surface)] border border-border/70 bg-card p-4"
		>
			<div className="flex flex-wrap items-start justify-between gap-3">
				<div className="min-w-0 space-y-2">
					<div className="flex flex-wrap items-center gap-2">
						<h3 className="min-w-0 font-mono text-sm font-medium [overflow-wrap:anywhere]">
							{rule.name}
						</h3>
						{rule.is_builtin && (
							<Badge
								variant="secondary"
								className="gap-1 text-xs"
								data-testid="builtin-badge"
							>
								<Lock className="h-3 w-3" />
								built-in
							</Badge>
						)}
					</div>
					<p className="text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]">
						{rule.description ?? "No description"}
					</p>
				</div>
			</div>

			<PolicyRuleActions
				rule={rule}
				onEdit={onEdit}
				onDelete={onDelete}
			/>
		</article>
	);
}
