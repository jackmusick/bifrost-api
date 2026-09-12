import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
	Sheet,
	SheetContent,
	SheetDescription,
	SheetFooter,
	SheetHeader,
	SheetTitle,
} from "@/components/ui/sheet";
import { useOrganizations } from "@/hooks/useOrganizations";
import { useDialogReturnFocus } from "@/hooks/useDialogReturnFocus";
export function KnowledgeAssignDrawer({
	onClose,
	onAssign,
}: {
	roleId: string;
	onClose: () => void;
	onAssign: (
		entries: { namespace: string; organization_id?: string | null }[],
	) => Promise<void>;
}) {
	const { data: orgs, isError, isFetching, refetch } = useOrganizations();
	const returnFocus = useDialogReturnFocus();
	const [error, setError] = useState<string | null>(null);
	const [namespace, setNamespace] = useState("");
	const [orgId, setOrgId] = useState<string>("global");
	const [submitting, setSubmitting] = useState(false);

	const handleSubmit = async () => {
		if (submitting) return;
		setError(null);
		const ns = namespace.trim();
		if (!ns) {
			setError("Namespace is required.");
			return;
		}
		setSubmitting(true);
		try {
			await onAssign([
				{
					namespace: ns,
					organization_id: orgId === "global" ? null : orgId,
				},
			]);
			toast.success(`Assigned namespace "${ns}"`);
			setNamespace("");
		} catch (e) {
			setError(
				"Namespace could not be assigned. Your entries are retained; try again.",
			);
			toast.error(
				e instanceof Error ? e.message : "Failed to assign namespace",
			);
		} finally {
			setSubmitting(false);
		}
	};

	return (
		<Sheet open onOpenChange={(o) => !o && !submitting && onClose()}>
			<SheetContent
				side="right"
				{...returnFocus}
				onEscapeKeyDown={(event) => {
					if (submitting) event.preventDefault();
				}}
				className="w-full sm:max-w-[480px] flex flex-col"
			>
				<SheetHeader>
					<SheetTitle>Assign knowledge namespace</SheetTitle>
					<SheetDescription>
						Grant this role access to a knowledge namespace.
						Namespaces are free-form strings — pick the one used in
						your knowledge store.
					</SheetDescription>
				</SheetHeader>

				<fieldset
					disabled={submitting}
					className="min-h-0 flex-1 overflow-y-auto px-6 py-2 space-y-5"
				>
					<label className="block text-sm">
						<span className="block mb-1 text-muted-foreground">
							Namespace
						</span>
						<Input
							type="text"
							className="h-11"
							value={namespace}
							onChange={(e) => setNamespace(e.target.value)}
							placeholder="e.g. customer-docs"
						/>
					</label>

					<label className="block text-sm">
						<span className="block mb-1 text-muted-foreground">
							Scope
						</span>
						<select
							aria-label="Scope"
							value={orgId}
							onChange={(e) => setOrgId(e.target.value)}
							className="h-11 w-full rounded-[var(--bf-radius-control)] border border-border/70 bg-background px-3 text-base md:text-sm outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/25 disabled:opacity-50"
						>
							<option value="global">All organizations</option>
							{(orgs ?? []).map((o) => (
								<option key={o.id} value={o.id}>
									{o.name}
								</option>
							))}
						</select>
					</label>
				</fieldset>

				{isError && (
					<div role="alert" className="px-6 text-sm">
						<p>Organization choices could not load.</p>
						<Button
							variant="outline"
							className="min-h-11"
							disabled={isFetching || submitting}
							onClick={() => void refetch()}
						>
							Retry organizations
						</Button>
					</div>
				)}
				{error && (
					<p role="alert" className="px-6 text-sm text-destructive">
						{error}
					</p>
				)}
				<SheetFooter>
					<Button
						variant="outline"
						className="min-h-11"
						disabled={submitting}
						onClick={onClose}
					>
						Close
					</Button>
					<Button
						className="min-h-11"
						disabled={submitting}
						onClick={handleSubmit}
					>
						{submitting ? "Assigning..." : "Assign"}
					</Button>
				</SheetFooter>
			</SheetContent>
		</Sheet>
	);
}
