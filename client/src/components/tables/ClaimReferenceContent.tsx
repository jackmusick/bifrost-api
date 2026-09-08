export function ClaimReferenceContent() {
	return (
		<div className="space-y-4 text-sm">
			<section className="space-y-2 rounded-[var(--bf-radius-surface)] border border-border/70 bg-card p-4">
				<h4 className="font-medium">What is a Custom Claim?</h4>
				<p className="text-muted-foreground leading-6">
					A query-resolved fact about the calling user. Table policies
					can reference it with <code>{"{ claims: <name> }"}</code>.
				</p>
			</section>

			<section className="space-y-2 rounded-[var(--bf-radius-surface)] border border-border/70 bg-card p-4">
				<h4 className="font-medium">Claim query</h4>
				<pre className="overflow-x-auto rounded-[var(--bf-radius-control)] border border-border/70 bg-muted p-3 text-xs leading-6">
					{`name: allowed_campus_ids
type: list
query:
  table: user_campus_access
  where:
    eq: [{ row: user_id }, { user: user_id }]
  select: campus_id`}
				</pre>
			</section>

			<section className="space-y-2 rounded-[var(--bf-radius-surface)] border border-border/70 bg-card p-4">
				<h4 className="font-medium">Policy reference</h4>
				<pre className="overflow-x-auto rounded-[var(--bf-radius-control)] border border-border/70 bg-muted p-3 text-xs leading-6">
					{`in: [{ row: campus_id }, { claims: allowed_campus_ids }]`}
				</pre>
			</section>
		</div>
	);
}
